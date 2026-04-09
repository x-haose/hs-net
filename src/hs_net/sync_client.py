from __future__ import annotations

import functools
import logging
from threading import Semaphore as ThreadSemaphore
from typing import Any

from tenacity import RetryCallState, Retrying, stop_after_attempt, wait_fixed, wait_random

from hs_net._request_builder import build_request
from hs_net._shared import format_retry_log, merge_config
from hs_net.config import NetConfig
from hs_net.engines.base import SyncEngineBase
from hs_net.engines.httpx_engine import SyncHttpxEngine
from hs_net.exceptions import RequestException, RetryExhausted
from hs_net.models import EngineEnum, RequestModel
from hs_net.proxy import ProxyService
from hs_net.rate_limit import RateLimitConfig, SyncRateLimitManager
from hs_net.response import Response
from hs_net.response.stream import StreamResponse
from hs_net.signals import SignalManager

logger = logging.getLogger("hs_net")


@functools.cache
def _get_sync_engine_map() -> dict[str, type[SyncEngineBase]]:
    """延迟构建同步引擎映射表（结果缓存，仅首次调用时导入）。

    避免在未安装可选依赖时因顶层 import 失败而导致整个包不可用。

    Returns:
        引擎名称到引擎类的映射字典。
    """
    from hs_net.engines.curl_cffi_engine import SyncCurlCffiEngine
    from hs_net.engines.requests_engine import SyncRequestsEngine
    from hs_net.engines.requests_go_engine import SyncRequestsGoEngine

    return {
        "httpx": SyncHttpxEngine,
        "curl_cffi": SyncCurlCffiEngine,
        "requests": SyncRequestsEngine,
        "requests_go": SyncRequestsGoEngine,
    }


def _resolve_sync_engine_cls(engine: str | EngineEnum | type[SyncEngineBase]) -> type[SyncEngineBase]:
    """根据引擎标识获取同步引擎类。

    Args:
        engine: 引擎标识，支持字符串、EngineEnum 枚举或 SyncEngineBase 子类。

    Returns:
        对应的同步引擎类。

    Raises:
        ValueError: 当引擎标识不被支持时抛出。
    """
    if isinstance(engine, type) and issubclass(engine, SyncEngineBase):
        return engine

    engine_value = engine.value if isinstance(engine, EngineEnum) else engine

    if engine_value == "aiohttp":
        raise ValueError("aiohttp 引擎不支持同步，请使用 Net 或选择其他引擎")

    engine_map = _get_sync_engine_map()
    if engine_value in engine_map:
        return engine_map[engine_value]

    raise ValueError(f"不支持的同步引擎: {engine_value}")


def _build_sync_rate_limiter(rate_limit) -> SyncRateLimitManager | None:
    """根据 rate_limit 配置构建同步限速管理器。"""
    if rate_limit is None:
        return None
    if isinstance(rate_limit, int | float):
        rate_limit = RateLimitConfig(rate=int(rate_limit))
    return SyncRateLimitManager(rate_limit)


class SyncNet:
    """
    同步 HTTP 客户端

    直接使用同步引擎，无需事件循环。支持多引擎切换、自动重试、信号中间件、选择器解析。

    用法::

        with SyncNet(engine="httpx") as net:
            resp = net.get("https://example.com")
            print(resp.css("title::text").get())
    """

    def __init__(
        self,
        engine: str | EngineEnum | type[SyncEngineBase] = None,
        *,
        base_url: str = None,
        timeout: float = None,
        retries: int = None,
        retry_delay: float = None,
        user_agent: str = None,
        proxy: str | ProxyService = None,
        verify: bool = None,
        raise_status: bool = None,
        allow_redirects: bool = None,
        rate_limit: int | float | RateLimitConfig = None,
        concurrency: int = None,
        headers: dict[str, Any] = None,
        cookies: dict[str, Any] = None,
        engine_options: dict[str, Any] = None,
        config: NetConfig = None,
    ):
        """初始化同步 HTTP 客户端。

        所有参数均可选，未指定的参数从 config（默认 NetConfig）中取值。
        构造函数参数优先级高于 config 中的值。

        Args:
            engine: HTTP 引擎，支持字符串、EngineEnum 或 SyncEngineBase 子类。
            base_url: 基础 URL，与请求路径拼接。
            timeout: 请求超时时间（秒）。
            retries: 请求失败后的重试次数。
            retry_delay: 重试间隔时间（秒）。
            user_agent: User-Agent，支持 "random"、"chrome" 等快捷方式。
            proxy: 代理配置，支持字符串、列表或 ProxyService。
            verify: 是否验证 SSL 证书。
            raise_status: 状态码非 2xx 时是否抛出异常。
            allow_redirects: 是否允许自动重定向。
            rate_limit: 速率限制，支持 int/float（每秒请求数）或 RateLimitConfig。
            concurrency: 最大并发数，为 None 则不限制。
            headers: 全局默认请求头。
            cookies: 全局默认 cookies。
            engine_options: 引擎特定配置（如 http2、impersonate 等）。
            config: NetConfig 配置对象，与其他参数合并（其他参数优先）。
        """
        # 所有代理统一走 ProxyService
        self._proxy_service: ProxyService | None = None
        proxy = proxy if proxy is not None else (config.proxy if config else None)
        if isinstance(proxy, ProxyService):
            self._proxy_service = proxy
        elif isinstance(proxy, str):
            self._proxy_service = ProxyService(proxy)
        if self._proxy_service:
            if not self._proxy_service.started:
                self._proxy_service.start()
            proxy = None  # 代理由引擎 engine_options 注入

        self._config = merge_config(
            config,
            engine=engine,
            base_url=base_url,
            timeout=timeout,
            retries=retries,
            retry_delay=retry_delay,
            user_agent=user_agent,
            proxy=proxy,
            verify=verify,
            raise_status=raise_status,
            allow_redirects=allow_redirects,
            rate_limit=rate_limit,
            concurrency=concurrency,
            headers=headers,
            cookies=cookies,
            engine_options=engine_options,
        )

        sem = ThreadSemaphore(self._config.concurrency) if self._config.concurrency else None
        engine_cls = _resolve_sync_engine_cls(self._config.engine)
        engine_options = dict(self._config.engine_options)
        if self._proxy_service and self._proxy_service.started:
            engine_options["proxy"] = self._proxy_service.local_url
        self._engine = engine_cls(
            sem=sem,
            headers=self._config.headers,
            cookies=self._config.cookies,
            verify=self._config.verify,
            **engine_options,
        )

        self._closed = False
        self._rate_limiter = _build_sync_rate_limiter(self._config.rate_limit)

        # 信号中间件
        self._signals = SignalManager()
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

    @property
    def proxy_service(self) -> ProxyService | None:
        """获取代理服务实例。"""
        return self._proxy_service

    def close(self):
        """关闭客户端，释放底层引擎和代理服务资源。"""
        if self._closed:
            return
        self._closed = True
        self._engine.close()
        if self._proxy_service and self._proxy_service.started:
            self._proxy_service.stop()

    def __del__(self):
        if not self._closed:
            import warnings

            warnings.warn(f"未关闭的 {self!r}，请使用 with 或手动调用 close()", ResourceWarning, stacklevel=2)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _retry_handler(self, req_data: RequestModel, retry_state: RetryCallState):
        """重试回调，记录日志并触发重试信号。

        Args:
            req_data: 请求模型。
            retry_state: tenacity 的重试状态对象。

        Raises:
            RetryExhausted: 当所有重试耗尽时抛出。
        """
        log_msg, attempt, exception = format_retry_log(req_data, retry_state)

        # 触发重试信号
        for _ in self._signals.send_sync(self._signals.request_retry, exception):
            ...

        if attempt == req_data.retries:
            logger.error(f"{log_msg} - {attempt} 次重试全部失败")
            raise RetryExhausted(attempts=attempt, last_exception=exception, url=req_data.url)

        logger.warning(f"{log_msg} - 第 {attempt} 次重试")

    def _do_request(self, data: RequestModel) -> Response:
        """执行单次请求，包含速率限制和请求前/响应后信号中间件。

        Args:
            data: 请求模型。

        Returns:
            Response 响应对象。
        """
        # 速率限制
        if self._rate_limiter:
            self._rate_limiter.acquire(data.url)

        # 请求前信号
        for _receiver, result in self._signals.send_sync(self._signals.request_before, data):
            if isinstance(result, RequestModel):
                data = result
            elif isinstance(result, Response):
                return result

        logger.debug(
            f"[{data.method}] {data.url} proxy={data.proxy} "
            f"params={data.url_params} json={data.json_data} form={data.form_data}"
        )

        resp = self._engine.download(data)

        # 响应后信号
        for _receiver, result in self._signals.send_sync(self._signals.response_after, resp):
            if isinstance(result, Response):
                return result

        return resp

    def request(
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

        try:
            if not data.retries or data.retries < 1:
                return self._do_request(data)

            wait = wait_fixed(data.retry_delay) + wait_random(0.1, 1) if data.retry_delay else wait_fixed(0)
            retry = Retrying(
                stop=stop_after_attempt(data.retries),
                after=functools.partial(self._retry_handler, data),
                retry_error_callback=functools.partial(self._retry_handler, data),
                wait=wait,
            )
            return retry.wraps(functools.partial(self._do_request, data))()
        except RequestException as e:
            raise e.with_traceback(None) from None

    def stream(
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
        raise_status: bool = None,
        allow_redirects: bool = None,
    ) -> StreamResponse:
        """发起流式 HTTP 请求。

        返回 StreamResponse 对象，支持迭代分块读取。
        使用后必须关闭，推荐使用 with::

            with sync_net.stream("GET", url) as resp:
                for chunk in resp:
                    f.write(chunk)

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
            raise_status: 是否抛出状态码异常。
            allow_redirects: 是否允许重定向。

        Returns:
            StreamResponse 流式响应对象。
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
            raise_status=raise_status,
            allow_redirects=allow_redirects,
        )
        try:
            return self._engine.stream(data)
        except RequestException as e:
            raise e.with_traceback(None) from None

    def get(self, url: str, *, params: dict = None, **kwargs) -> Response:
        """发起 GET 请求。

        Args:
            url: 请求目标 URL。
            params: URL 查询参数。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("GET", url, params=params, **kwargs)

    def post(
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
        return self.request("POST", url, params=params, json_data=json_data, form_data=form_data, files=files, **kwargs)

    def head(self, url: str, *, params: dict = None, **kwargs) -> Response:
        """发起 HEAD 请求。

        Args:
            url: 请求目标 URL。
            params: URL 查询参数。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("HEAD", url, params=params, **kwargs)

    def put(self, url: str, *, json_data: dict = None, **kwargs) -> Response:
        """发起 PUT 请求。

        Args:
            url: 请求目标 URL。
            json_data: JSON 请求体。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("PUT", url, json_data=json_data, **kwargs)

    def patch(self, url: str, *, json_data: dict = None, **kwargs) -> Response:
        """发起 PATCH 请求。

        Args:
            url: 请求目标 URL。
            json_data: JSON 请求体。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("PATCH", url, json_data=json_data, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        """发起 DELETE 请求。

        Args:
            url: 请求目标 URL。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("DELETE", url, **kwargs)

    def options(self, url: str, **kwargs) -> Response:
        """发起 OPTIONS 请求。

        Args:
            url: 请求目标 URL。
            **kwargs: 传递给 request() 的其他参数。

        Returns:
            Response 响应对象。
        """
        return self.request("OPTIONS", url, **kwargs)
