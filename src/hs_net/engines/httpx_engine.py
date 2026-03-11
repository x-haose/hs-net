from __future__ import annotations

from asyncio import Semaphore
from json import JSONDecodeError
from threading import Semaphore as ThreadSemaphore
from typing import Any

from httpx import AsyncClient, Client

from hs_net.exceptions import StatusException
from hs_net.models import RequestModel
from hs_net.response import Response

from .base import EngineBase, SyncEngineBase


def _parse_response(response, request_data: RequestModel, client_cookies: dict[str, str]) -> Response:
    """将 httpx 响应转换为统一的 Response 对象。

    Args:
        response: httpx 响应对象。
        request_data: 请求模型。
        client_cookies: 客户端会话 cookies。

    Returns:
        统一的 Response 响应对象。

    Raises:
        StatusException: 当 raise_status 为 True 且状态码非 2xx 时抛出。
    """
    if not response.is_success and request_data.raise_status:
        raise StatusException(code=response.status_code, url=request_data.url)

    try:
        json_data = response.json()
    except (JSONDecodeError, UnicodeDecodeError):
        json_data = None

    try:
        text_data = response.text
    except UnicodeDecodeError:
        text_data = ""

    resp_cookies = {cookie.name: cookie.value for cookie in response.cookies.jar}
    return Response(
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        cookies=resp_cookies,
        client_cookies=client_cookies,
        content=response.content,
        text=text_data,
        json_data=json_data,
        request_data=request_data,
    )


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

        self.client = AsyncClient(
            verify=self._verify,
            http2=engine_options.get("http2", True),
            headers=self._default_headers,
            cookies=self._default_cookies,
        )

    async def close(self):
        """关闭 httpx 客户端。"""
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
        """
        request = self.client.build_request(
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
        response = await self.client.send(request, follow_redirects=request_data.allow_redirects)
        return _parse_response(response, request_data, self.cookies)


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

        self.client = Client(
            verify=self._verify,
            http2=engine_options.get("http2", True),
            headers=self._default_headers,
            cookies=self._default_cookies,
        )

    def close(self):
        """关闭 httpx 客户端。"""
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
        """
        request = self.client.build_request(
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
        response = self.client.send(request, follow_redirects=request_data.allow_redirects)
        return _parse_response(response, request_data, self.cookies)
