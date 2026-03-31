from __future__ import annotations

from asyncio import Semaphore
from json import JSONDecodeError
from threading import Semaphore as ThreadSemaphore
from typing import Any

try:
    from requests.utils import cookiejar_from_dict, dict_from_cookiejar
    from requests_go import AsyncSession, Session

    _HAS_REQUESTS_GO = True
except ImportError:
    _HAS_REQUESTS_GO = False

from hs_net.exceptions import EngineNotInstalled, StatusException
from hs_net.models import RequestModel
from hs_net.response import Response

from .base import EngineBase, SyncEngineBase


def _parse_response(response, request_data: RequestModel, client_cookies: dict[str, str]) -> Response:
    """将 requests-go 响应转换为统一的 Response 对象。

    Args:
        response: requests-go 响应对象。
        request_data: 请求模型。
        client_cookies: 客户端会话 cookies。

    Returns:
        统一的 Response 响应对象。

    Raises:
        StatusException: 当 raise_status 为 True 且状态码非 2xx 时抛出。
    """
    if not response.ok and request_data.raise_status:
        raise StatusException(code=response.status_code, url=request_data.url)

    try:
        resp_json = response.json()
    except (JSONDecodeError, UnicodeDecodeError):
        resp_json = None

    return Response(
        url=str(response.url),
        status_code=response.status_code,
        headers=dict(response.headers),
        cookies=dict_from_cookiejar(response.cookies),
        client_cookies=client_cookies,
        content=response.content,
        text=response.text,
        json_data=resp_json,
        request_data=request_data,
    )


def _build_request_kwargs(request_data: RequestModel) -> dict:
    """构建 requests-go 请求参数。

    Args:
        request_data: 请求模型。

    Returns:
        请求参数字典。
    """
    proxies = {"https": request_data.proxy, "http": request_data.proxy} if request_data.proxy else None
    return {
        "method": request_data.method,
        "url": request_data.url,
        "params": request_data.url_params,
        "data": request_data.form_data if not request_data.files else None,
        "json": request_data.json_data,
        "files": request_data.files,
        "cookies": request_data.cookies,
        "headers": request_data.headers,
        "proxies": proxies,
        "timeout": request_data.timeout,
        "allow_redirects": request_data.allow_redirects,
    }


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
        """
        response = await self.client.async_request(**_build_request_kwargs(request_data))
        return _parse_response(response, request_data, self.cookies)


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
        """
        response = self.client.request(**_build_request_kwargs(request_data))
        return _parse_response(response, request_data, self.cookies)
