from __future__ import annotations

import functools
import logging
from asyncio import Semaphore
from typing import Any

from tenacity import AsyncRetrying, Future, RetryCallState, stop_after_attempt, wait_fixed, wait_random

from hs_net._request_builder import build_request
from hs_net.config import NetConfig
from hs_net.engines.base import EngineBase
from hs_net.engines.httpx_engine import HttpxEngine
from hs_net.exceptions import RetryExhausted, StatusException
from hs_net.models import EngineEnum, RequestModel
from hs_net.response import Response
from hs_net.signals import SignalManager

logger = logging.getLogger("hs_net")


def _get_async_engine_map() -> dict[str, type[EngineBase]]:
    """延迟构建异步引擎映射表。

    仅在首次调用时导入各引擎模块，避免在未安装可选依赖时
    因顶层 import 失败而导致整个包不可用。

    Returns:
        引擎名称到引擎类的映射字典。
    """
    from hs_net.engines.aiohttp_engine import AiohttpEngine
    from hs_net.engines.curl_cffi_engine import CurlCffiEngine
    from hs_net.engines.requests_go_engine import RequestsGoEngine

    return {
        "httpx": HttpxEngine,
        "aiohttp": AiohttpEngine,
        "curl_cffi": CurlCffiEngine,
        "requests_go": RequestsGoEngine,
    }


def _resolve_async_engine_cls(engine: str | EngineEnum | type[EngineBase]) -> type[EngineBase]:
    """根据引擎标识获取异步引擎类。

    Args:
        engine: 引擎标识，支持字符串、EngineEnum 枚举或 EngineBase 子类。

    Returns:
        对应的异步引擎类。

    Raises:
        ValueError: 当引擎标识不被支持时抛出。
    """
    if isinstance(engine, type) and issubclass(engine, EngineBase):
        return engine

    engine_value = engine.value if isinstance(engine, EngineEnum) else engine

    if engine_value == "requests":
        raise ValueError("requests 引擎不支持异步，请使用 SyncNet 或选择其他引擎")

    engine_map = _get_async_engine_map()
    if engine_value in engine_map:
        return engine_map[engine_value]

    raise ValueError(f"不支持的异步引擎: {engine_value}")


class Net:
    """
    统一的异步 HTTP 客户端

    支持多引擎切换、自动重试、信号中间件、选择器解析。

    用法::

        net = Net(engine="httpx", retries=3, user_agent="random")
        resp = await net.get("https://example.com")
        print(resp.css("title::text").get())
        await net.close()

    或使用 async with::

        async with Net() as net:
            resp = await net.get("https://example.com")
    """

    def __init__(
        self,
        engine: str | EngineEnum | type[EngineBase] = None,
        *,
        base_url: str = None,
        timeout: float = None,
        retries: int = None,
        retry_delay: float = None,
        user_agent: str = None,
        proxy: str = None,
        verify: bool = None,
        raise_status: bool = None,
        allow_redirects: bool = None,
        concurrency: int = None,
        headers: dict[str, Any] = None,
        cookies: dict[str, Any] = None,
        engine_options: dict[str, Any] = None,
        config: NetConfig = None,
    ):
        """初始化异步 HTTP 客户端。

        所有参数均可选，未指定的参数从 config（默认 NetConfig）中取值。
        构造函数参数优先级高于 config 中的值。

        Args:
            engine: HTTP 引擎，支持字符串、EngineEnum 或 EngineBase 子类。
            base_url: 基础 URL，与请求路径拼接。
            timeout: 请求超时时间（秒）。
            retries: 请求失败后的重试次数。
            retry_delay: 重试间隔时间（秒）。
            user_agent: User-Agent，支持 "random"、"chrome" 等快捷方式。
            proxy: 全局代理地址。
            verify: 是否验证 SSL 证书。
            raise_status: 状态码非 2xx 时是否抛出异常。
            allow_redirects: 是否允许自动重定向。
            concurrency: 最大并发数，为 None 则不限制。
            headers: 全局默认请求头。
            cookies: 全局默认 cookies。
            engine_options: 引擎特定配置（如 http2、impersonate 等）。
            config: NetConfig 配置对象，与其他参数合并（其他参数优先）。
        """
        cfg = config or NetConfig()

        self._config = NetConfig(
            engine=engine or cfg.engine,
            base_url=base_url if base_url is not None else cfg.base_url,
            timeout=timeout if timeout is not None else cfg.timeout,
            retries=retries if retries is not None else cfg.retries,
            retry_delay=retry_delay if retry_delay is not None else cfg.retry_delay,
            user_agent=user_agent or cfg.user_agent,
            proxy=proxy if proxy is not None else cfg.proxy,
            verify=verify if verify is not None else cfg.verify,
            raise_status=raise_status if raise_status is not None else cfg.raise_status,
            allow_redirects=allow_redirects if allow_redirects is not None else cfg.allow_redirects,
            concurrency=concurrency if concurrency is not None else cfg.concurrency,
            headers={**cfg.headers, **(headers or {})},
            cookies={**cfg.cookies, **(cookies or {})},
            engine_options={**cfg.engine_options, **(engine_options or {})},
        )

        sem = Semaphore(self._config.concurrency) if self._config.concurrency else None
        engine_cls = _resolve_async_engine_cls(self._config.engine)
        self._engine = engine_cls(
            sem=sem,
            headers=self._config.headers,
            cookies=self._config.cookies,
            verify=self._config.verify,
            **self._config.engine_options,
        )

        # 信号中间件
        self._signals = SignalManager(id(self))
        self.on_request_before = self._signals.on_request_before
        self.on_response_after = self._signals.on_response_after
        self.on_request_retry = self._signals.on_request_retry

    @property
    def cookies(self) -> dict[str, str]:
        """获取当前会话的 cookies。

        Returns:
            cookies 字典。
        """
        return self._engine.cookies

    async def close(self):
        """关闭客户端，释放底层引擎资源。"""
        await self._engine.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def _retry_handler(self, req_data: RequestModel, retry_state: RetryCallState):
        """重试回调，记录日志并触发重试信号。

        Args:
            req_data: 请求模型。
            retry_state: tenacity 的重试状态对象。

        Raises:
            RetryExhausted: 当所有重试耗尽时抛出。
        """
        outcome: Future = retry_state.outcome
        attempt = retry_state.attempt_number
        exception = outcome.exception()
        exc_type = type(exception).__name__
        exc_msg = str(exception)

        # 触发重试信号
        async for _ in self._signals.send(self._signals.request_retry, exception):
            ...

        if isinstance(exception, StatusException):
            exc_msg = f"HTTP {exception.code}"

        log_msg = f"[{req_data.method}] {req_data.url} proxy={req_data.proxy} error=[{exc_type}]: {exc_msg}"

        if attempt == req_data.retries:
            logger.error(f"{log_msg} - {attempt} 次重试全部失败")
            raise RetryExhausted(attempts=attempt, last_exception=exception, url=req_data.url)

        logger.warning(f"{log_msg} - 第 {attempt} 次重试")

    async def _do_request(self, data: RequestModel) -> Response:
        """执行单次请求，包含请求前/响应后信号中间件。

        Args:
            data: 请求模型。

        Returns:
            Response 响应对象。
        """
        # 请求前信号
        async for _receiver, result in self._signals.send(self._signals.request_before, data):
            if isinstance(result, RequestModel):
                data = result
            elif isinstance(result, Response):
                return result

        logger.debug(
            f"[{data.method}] {data.url} proxy={data.proxy} "
            f"params={data.url_params} json={data.json_data} form={data.form_data}"
        )

        resp = await self._engine.download(data)

        # 响应后信号
        async for _receiver, result in self._signals.send(self._signals.response_after, resp):
            if isinstance(result, Response):
                return result

        return resp

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: dict = None,
        json_data: dict = None,
        form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None,
        files: dict[str, Any] | list[tuple] | None = None,
        user_agent: str = None,
        headers: dict = None,
        cookies: dict = None,
        timeout: float = None,
        proxy: str = None,
        verify: bool = None,
        retries: int = None,
        retry_delay: float = None,
        raise_status: bool = None,
        allow_redirects: bool = None,
    ) -> Response:
        """发起 HTTP 请求，支持自动重试。

        所有参数（除 method 和 url 外）均可选，未指定则使用实例配置。

        Args:
            method: HTTP 方法（GET、POST、PUT 等）。
            url: 请求目标 URL。
            params: URL 查询参数。
            json_data: JSON 请求体。
            form_data: 表单数据。
            files: 文件上传数据。
            user_agent: User-Agent。
            headers: 请求头。
            cookies: cookies。
            timeout: 超时时间（秒）。
            proxy: 代理地址。
            verify: 是否验证 SSL 证书。
            retries: 重试次数。
            retry_delay: 重试间隔（秒）。
            raise_status: 是否抛出状态码异常。
            allow_redirects: 是否允许重定向。

        Returns:
            Response 响应对象。

        Raises:
            RetryExhausted: 当所有重试耗尽时抛出。
            StatusException: 当 raise_status 为 True 且状态码非 2xx 时抛出。
        """
        data = build_request(
            self._config,
            url=url,
            method=method,
            params=params,
            json_data=json_data,
            form_data=form_data,
            files=files,
            user_agent=user_agent,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy=proxy,
            verify=verify,
            retries=retries,
            retry_delay=retry_delay,
            raise_status=raise_status,
            allow_redirects=allow_redirects,
        )

        if not data.retries or data.retries < 1:
            return await self._do_request(data)

        wait = wait_fixed(data.retry_delay) + wait_random(0.1, 1) if data.retry_delay else wait_fixed(0)
        retry = AsyncRetrying(
            stop=stop_after_attempt(data.retries),
            after=functools.partial(self._retry_handler, data),
            retry_error_callback=functools.partial(self._retry_handler, data),
            wait=wait,
        )
        return await retry.wraps(functools.partial(self._do_request, data))()

    async def get(self, url: str, *, params: dict = None, **kwargs) -> Response:
        """发起 GET 请求。

        Args:
            url: 请求目标 URL。
            params: URL 查询参数。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("GET", url, params=params, **kwargs)

    async def post(
        self,
        url: str,
        *,
        params: dict = None,
        json_data: dict = None,
        form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None,
        files: dict[str, Any] | list[tuple] | None = None,
        **kwargs,
    ) -> Response:
        """发起 POST 请求。

        Args:
            url: 请求目标 URL。
            params: URL 查询参数。
            json_data: JSON 请求体。
            form_data: 表单数据。
            files: 文件上传数据。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request(
            "POST", url, params=params, json_data=json_data, form_data=form_data, files=files, **kwargs
        )

    async def head(self, url: str, *, params: dict = None, **kwargs) -> Response:
        """发起 HEAD 请求。

        Args:
            url: 请求目标 URL。
            params: URL 查询参数。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("HEAD", url, params=params, **kwargs)

    async def put(self, url: str, *, json_data: dict = None, **kwargs) -> Response:
        """发起 PUT 请求。

        Args:
            url: 请求目标 URL。
            json_data: JSON 请求体。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("PUT", url, json_data=json_data, **kwargs)

    async def patch(self, url: str, *, json_data: dict = None, **kwargs) -> Response:
        """发起 PATCH 请求。

        Args:
            url: 请求目标 URL。
            json_data: JSON 请求体。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("PATCH", url, json_data=json_data, **kwargs)

    async def delete(self, url: str, **kwargs) -> Response:
        """发起 DELETE 请求。

        Args:
            url: 请求目标 URL。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("DELETE", url, **kwargs)

    async def options(self, url: str, **kwargs) -> Response:
        """发起 OPTIONS 请求。

        Args:
            url: 请求目标 URL。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return await self.request("OPTIONS", url, **kwargs)
