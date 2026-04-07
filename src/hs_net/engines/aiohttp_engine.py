from __future__ import annotations

from asyncio import Semaphore
from typing import Any

try:
    import aiohttp
    from aiohttp import ClientSession, ClientTimeout, TCPConnector

    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

from hs_net.exceptions import ConnectionException, EngineNotInstalled, StatusException, TimeoutException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse

from .base import EngineBase, build_response


class AiohttpEngine(EngineBase):
    """基于 aiohttp 的异步 HTTP 引擎。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化 aiohttp 引擎。

        Args:
            sem: 信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: aiohttp 特定配置。
        """
        if not _HAS_AIOHTTP:
            raise EngineNotInstalled("aiohttp", "hs-net[aiohttp]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        self.client = ClientSession(
            headers=self._default_headers,
            cookies=self._default_cookies,
            connector=TCPConnector(ssl=self._verify if self._verify else False),
            trust_env=True,
        )

    async def close(self):
        """关闭 aiohttp 客户端。"""
        await self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return {cookie.key: cookie.value for cookie in self.client.cookie_jar}

    async def _download(self, request_data: RequestModel) -> Response:
        """使用 aiohttp 执行 HTTP 请求。

        Args:
            request_data: 请求模型。

        Returns:
            统一的 Response 响应对象。

        Raises:
            StatusException: 当 raise_status 为 True 且状态码非 2xx 时抛出。
            TimeoutException: 当请求超时时抛出。
            ConnectionException: 当连接失败时抛出。
        """
        try:
            timeout = ClientTimeout(total=request_data.timeout)
            response = await self.client.request(
                method=request_data.method,
                url=request_data.url,
                params=request_data.url_params,
                data=request_data.form_data if not request_data.files else None,
                json=request_data.json_data,
                cookies=request_data.cookies,
                headers=request_data.headers,
                proxy=request_data.proxy,
                timeout=timeout,
                allow_redirects=request_data.allow_redirects,
            )

            resp_content = await response.read()
            resp_cookies = {name: cookie.value for name, cookie in response.cookies.items()}

            return build_response(
                url=str(response.url),
                status_code=response.status,
                headers=dict(response.headers),
                cookies=resp_cookies,
                client_cookies=self.cookies,
                content=resp_content,
                request_data=request_data,
            )
        except TimeoutError as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except aiohttp.ClientConnectorError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e

    async def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 aiohttp 执行异步流式 HTTP 请求。

        Args:
            request_data: 请求模型。

        Returns:
            StreamResponse 流式响应对象。

        Raises:
            StatusException: 当 raise_status 为 True 且状态码非 2xx 时抛出。
            TimeoutException: 当请求超时时抛出。
            ConnectionException: 当连接失败时抛出。
        """
        try:
            timeout = ClientTimeout(total=request_data.timeout)
            response = await self.client.request(
                method=request_data.method,
                url=request_data.url,
                params=request_data.url_params,
                data=request_data.form_data if not request_data.files else None,
                json=request_data.json_data,
                cookies=request_data.cookies,
                headers=request_data.headers,
                proxy=request_data.proxy,
                timeout=timeout,
                allow_redirects=request_data.allow_redirects,
            )

            if not response.ok and request_data.raise_status:
                response.release()
                raise StatusException(code=response.status, url=request_data.url)

            return StreamResponse(
                url=str(response.url),
                status_code=response.status,
                headers=dict(response.headers),
                cookies={name: cookie.value for name, cookie in response.cookies.items()},
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.content.iter_any(),
                close_callback=response.release,
            )
        except TimeoutError as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except aiohttp.ClientConnectorError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e
