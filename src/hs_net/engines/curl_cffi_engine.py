from __future__ import annotations

from asyncio import Semaphore
from threading import Semaphore as ThreadSemaphore
from typing import Any

try:
    import curl_cffi.requests.errors
    from curl_cffi.const import CurlHttpVersion
    from curl_cffi.requests import AsyncSession, Session

    _HAS_CURL_CFFI = True
except ImportError:
    _HAS_CURL_CFFI = False

from hs_net.exceptions import ConnectionException, EngineNotInstalled, StatusException, TimeoutException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse

from .base import EngineBase, SyncEngineBase, build_common_request_kwargs, build_response


class CurlCffiEngine(EngineBase):
    """基于 curl-cffi 的异步 HTTP 引擎，支持浏览器 TLS 指纹模拟。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化异步 curl-cffi 引擎。

        Args:
            sem: 信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: curl-cffi 特定配置（如 impersonate、http_version）。
        """
        if not _HAS_CURL_CFFI:
            raise EngineNotInstalled("curl-cffi", "hs-net[curl]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        proxy = engine_options.get("proxy")
        self.client = AsyncSession(
            verify=self._verify,
            headers=self._default_headers,
            cookies=self._default_cookies,
            impersonate=engine_options.get("impersonate", "chrome110"),
            http_version=engine_options.get("http_version", CurlHttpVersion.V2_0),
            proxy=proxy,
        )

    async def close(self):
        """关闭 curl-cffi 客户端。"""
        await self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return self.client.cookies.get_dict()

    async def _download(self, request_data: RequestModel) -> Response:
        """使用 curl-cffi 执行异步 HTTP 请求。

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
            response = await self.client.request(**build_common_request_kwargs(request_data))
            return build_response(
                url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=response.cookies.get_dict(),
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
            raise ConnectionException(url=request_data.url, message=str(e)) from None

    async def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 curl-cffi 执行异步流式 HTTP 请求。

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
            kwargs = build_common_request_kwargs(request_data)
            kwargs["stream"] = True
            response = await self.client.request(**kwargs)

            if not response.ok and request_data.raise_status:
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=response.cookies.get_dict(),
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.iter_content(),
                close_callback=response.close,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
            raise ConnectionException(url=request_data.url, message=str(e)) from None


class SyncCurlCffiEngine(SyncEngineBase):
    """基于 curl-cffi 的同步 HTTP 引擎，支持浏览器 TLS 指纹模拟。"""

    def __init__(
        self,
        sem: ThreadSemaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化同步 curl-cffi 引擎。

        Args:
            sem: 线程信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: curl-cffi 特定配置（如 impersonate、http_version）。
        """
        if not _HAS_CURL_CFFI:
            raise EngineNotInstalled("curl-cffi", "hs-net[curl]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        proxy = engine_options.get("proxy")
        self.client = Session(
            verify=self._verify,
            headers=self._default_headers,
            cookies=self._default_cookies,
            impersonate=engine_options.get("impersonate", "chrome110"),
            http_version=engine_options.get("http_version", CurlHttpVersion.V2_0),
            proxy=proxy,
        )

    def close(self):
        """关闭 curl-cffi 客户端。"""
        self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return self.client.cookies.get_dict()

    def _download(self, request_data: RequestModel) -> Response:
        """使用 curl-cffi 执行同步 HTTP 请求。

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
            response = self.client.request(**build_common_request_kwargs(request_data))
            return build_response(
                url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=response.cookies.get_dict(),
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
            raise ConnectionException(url=request_data.url, message=str(e)) from None

    def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 curl-cffi 执行同步流式 HTTP 请求。

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
            kwargs = build_common_request_kwargs(request_data)
            kwargs["stream"] = True
            response = self.client.request(**kwargs)

            if not response.ok and request_data.raise_status:
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=response.url,
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=response.cookies.get_dict(),
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.iter_content(),
                close_callback=response.close,
            )
        except curl_cffi.requests.errors.RequestsError as e:
            err_msg = str(e).lower()
            if "timeout" in err_msg:
                raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
            raise ConnectionException(url=request_data.url, message=str(e)) from None
