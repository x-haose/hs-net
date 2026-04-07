from __future__ import annotations

from asyncio import Semaphore
from threading import Semaphore as ThreadSemaphore
from typing import Any

try:
    import requests
    from requests.utils import cookiejar_from_dict, dict_from_cookiejar
    from requests_go import AsyncSession, Session

    _HAS_REQUESTS_GO = True
except ImportError:
    _HAS_REQUESTS_GO = False

from hs_net.exceptions import ConnectionException, EngineNotInstalled, StatusException, TimeoutException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse

from .base import EngineBase, SyncEngineBase, build_common_request_kwargs, build_response


class RequestsGoEngine(EngineBase):
    """基于 requests-go 的异步 HTTP 引擎，底层使用 Go 实现。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化异步 requests-go 引擎。

        Args:
            sem: 信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: requests-go 特定配置。
        """
        if not _HAS_REQUESTS_GO:
            raise EngineNotInstalled("requests-go", "hs-net[requests-go]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        self.client = AsyncSession()
        self.client.verify = self._verify
        self.client.headers.update(self._default_headers)
        self.client.cookies = cookiejar_from_dict(self._default_cookies)

    async def close(self):
        """关闭 requests-go 客户端。"""
        self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return dict_from_cookiejar(self.client.cookies)

    async def _download(self, request_data: RequestModel) -> Response:
        """使用 requests-go 执行异步 HTTP 请求。

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
            response = await self.client.async_request(**build_common_request_kwargs(request_data))
            return build_response(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict_from_cookiejar(response.cookies),
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except requests.Timeout as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e

    async def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 requests-go 执行异步流式 HTTP 请求。

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
            response = await self.client.async_request(**kwargs)

            if not response.ok and request_data.raise_status:
                response.close()
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict_from_cookiejar(response.cookies),
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.iter_content(chunk_size=8192),
                close_callback=response.close,
            )
        except requests.Timeout as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e


class SyncRequestsGoEngine(SyncEngineBase):
    """基于 requests-go 的同步 HTTP 引擎，底层使用 Go 实现。"""

    def __init__(
        self,
        sem: ThreadSemaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化同步 requests-go 引擎。

        Args:
            sem: 线程信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: requests-go 特定配置。
        """
        if not _HAS_REQUESTS_GO:
            raise EngineNotInstalled("requests-go", "hs-net[requests-go]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        self.client = Session()
        self.client.verify = self._verify
        self.client.headers.update(self._default_headers)
        self.client.cookies = cookiejar_from_dict(self._default_cookies)

    def close(self):
        """关闭 requests-go 客户端。"""
        self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return dict_from_cookiejar(self.client.cookies)

    def _download(self, request_data: RequestModel) -> Response:
        """使用 requests-go 执行同步 HTTP 请求。

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
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict_from_cookiejar(response.cookies),
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except requests.Timeout as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e

    def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 requests-go 执行同步流式 HTTP 请求。

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
                response.close()
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict_from_cookiejar(response.cookies),
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.iter_content(chunk_size=8192),
                close_callback=response.close,
            )
        except requests.Timeout as e:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from e
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from e
