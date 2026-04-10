from __future__ import annotations

from asyncio import Semaphore
from threading import Semaphore as ThreadSemaphore
from typing import Any

import httpx
from httpx import AsyncClient, Client

from hs_net.exceptions import ConnectionException, StatusException, TimeoutException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse

from .base import EngineBase, SyncEngineBase, build_response


class HttpxEngine(EngineBase):
    """基于 httpx 的异步 HTTP 引擎，支持 HTTP/2。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化 httpx 异步引擎。

        Args:
            sem: 信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: httpx 特定配置（如 http2）。
        """
        super().__init__(sem, headers, cookies, verify, **engine_options)

        proxy = engine_options.get("proxy")
        self._http2 = engine_options.get("http2", True)
        self.client = AsyncClient(
            verify=self._verify,
            http2=self._http2,
            headers=self._default_headers,
            cookies=self._default_cookies,
            proxy=proxy,
        )
        self._proxy_clients: dict[str, AsyncClient] = {}

    def _get_client(self, proxy: str | None) -> AsyncClient:
        """获取对应代理的 httpx 客户端，支持 per-request 代理（身份路由场景）。"""
        if not proxy:
            return self.client
        if proxy not in self._proxy_clients:
            self._proxy_clients[proxy] = AsyncClient(
                verify=self._verify,
                http2=self._http2,
                headers=self._default_headers,
                cookies=self._default_cookies,
                proxy=proxy,
            )
        return self._proxy_clients[proxy]

    async def close(self):
        """关闭 httpx 客户端。"""
        for client in self._proxy_clients.values():
            await client.aclose()
        self._proxy_clients.clear()
        await self.client.aclose()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return {cookie.name: cookie.value for cookie in self.client.cookies.jar}

    async def _download(self, request_data: RequestModel) -> Response:
        """使用 httpx 执行异步 HTTP 请求。

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
            client = self._get_client(request_data.proxy)
            request = client.build_request(
                request_data.method,
                request_data.url,
                headers=request_data.headers,
                timeout=request_data.timeout,
                cookies=request_data.cookies,
                params=request_data.url_params,
                data=request_data.form_data,
                json=request_data.json_data,
                files=request_data.files,
            )
            response = await client.send(request, follow_redirects=request_data.allow_redirects)
            return build_response(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies={cookie.name: cookie.value for cookie in response.cookies.jar},
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except httpx.TimeoutException:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except httpx.ConnectError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None

    async def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 httpx 执行异步流式 HTTP 请求。

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
            client = self._get_client(request_data.proxy)
            request = client.build_request(
                request_data.method,
                request_data.url,
                headers=request_data.headers,
                timeout=request_data.timeout,
                cookies=request_data.cookies,
                params=request_data.url_params,
                data=request_data.form_data,
                json=request_data.json_data,
                files=request_data.files,
            )
            response = await client.send(
                request,
                follow_redirects=request_data.allow_redirects,
                stream=True,
            )

            if not response.is_success and request_data.raise_status:
                await response.aclose()
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies={cookie.name: cookie.value for cookie in response.cookies.jar},
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.aiter_bytes(),
                close_callback=response.aclose,
            )
        except httpx.TimeoutException:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except httpx.ConnectError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None


class SyncHttpxEngine(SyncEngineBase):
    """基于 httpx 的同步 HTTP 引擎，支持 HTTP/2。"""

    def __init__(
        self,
        sem: ThreadSemaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化 httpx 同步引擎。

        Args:
            sem: 线程信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: httpx 特定配置（如 http2）。
        """
        super().__init__(sem, headers, cookies, verify, **engine_options)

        proxy = engine_options.get("proxy")
        self._http2 = engine_options.get("http2", True)
        self.client = Client(
            verify=self._verify,
            http2=self._http2,
            headers=self._default_headers,
            cookies=self._default_cookies,
            proxy=proxy,
        )
        self._proxy_clients: dict[str, Client] = {}

    def _get_client(self, proxy: str | None) -> Client:
        """获取对应代理的 httpx 客户端，支持 per-request 代理（身份路由场景）。"""
        if not proxy:
            return self.client
        if proxy not in self._proxy_clients:
            self._proxy_clients[proxy] = Client(
                verify=self._verify,
                http2=self._http2,
                headers=self._default_headers,
                cookies=self._default_cookies,
                proxy=proxy,
            )
        return self._proxy_clients[proxy]

    def close(self):
        """关闭 httpx 客户端。"""
        for client in self._proxy_clients.values():
            client.close()
        self._proxy_clients.clear()
        self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return {cookie.name: cookie.value for cookie in self.client.cookies.jar}

    def _download(self, request_data: RequestModel) -> Response:
        """使用 httpx 执行同步 HTTP 请求。

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
            client = self._get_client(request_data.proxy)
            request = client.build_request(
                request_data.method,
                request_data.url,
                headers=request_data.headers,
                timeout=request_data.timeout,
                cookies=request_data.cookies,
                params=request_data.url_params,
                data=request_data.form_data,
                json=request_data.json_data,
                files=request_data.files,
            )
            response = client.send(request, follow_redirects=request_data.allow_redirects)
            return build_response(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies={cookie.name: cookie.value for cookie in response.cookies.jar},
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except httpx.TimeoutException:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except httpx.ConnectError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None

    def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 httpx 执行同步流式 HTTP 请求。

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
            client = self._get_client(request_data.proxy)
            request = client.build_request(
                request_data.method,
                request_data.url,
                headers=request_data.headers,
                timeout=request_data.timeout,
                cookies=request_data.cookies,
                params=request_data.url_params,
                data=request_data.form_data,
                json=request_data.json_data,
                files=request_data.files,
            )
            response = client.send(
                request,
                follow_redirects=request_data.allow_redirects,
                stream=True,
            )

            if not response.is_success and request_data.raise_status:
                response.close()
                raise StatusException(code=response.status_code, url=request_data.url)

            return StreamResponse(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies={cookie.name: cookie.value for cookie in response.cookies.jar},
                client_cookies=self.cookies,
                request_data=request_data,
                stream=response.iter_bytes(),
                close_callback=response.close,
            )
        except httpx.TimeoutException:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except httpx.ConnectError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None
