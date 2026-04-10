from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Semaphore
from threading import Semaphore as ThreadSemaphore
from typing import Any

from hs_net.exceptions import StatusException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse


def build_response(
    *,
    url: str,
    status_code: int,
    headers: dict,
    cookies: dict[str, str],
    client_cookies: dict[str, str],
    content: bytes,
    request_data: RequestModel,
) -> Response:
    """统一构造 Response 对象，包含状态码检查。"""
    if not (200 <= status_code < 300) and request_data.raise_status:
        raise StatusException(code=status_code, url=request_data.url)
    return Response(
        url=url,
        status_code=status_code,
        headers=headers,
        cookies=cookies,
        client_cookies=client_cookies,
        content=content,
        request_data=request_data,
    )


def build_common_request_kwargs(request_data: RequestModel) -> dict:
    """构建 curl-cffi / requests / requests-go 共用的请求参数。"""
    return {
        "method": request_data.method,
        "url": request_data.url,
        "params": request_data.url_params,
        "data": request_data.form_data if not request_data.files else None,
        "json": request_data.json_data,
        "files": request_data.files,
        "cookies": request_data.cookies,
        "headers": request_data.headers,
        "timeout": request_data.timeout,
        "allow_redirects": request_data.allow_redirects,
    }


class EngineBase(ABC):
    """异步 HTTP 引擎基类，所有异步引擎需实现此接口。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化异步引擎基类。

        Args:
            sem: 异步信号量，用于控制并发请求数量，为 None 则不限制。
            headers: 默认请求头，会应用到所有请求。
            cookies: 默认 cookies，会应用到所有请求。
            verify: 是否验证 SSL 证书。
            **engine_options: 引擎特定配置，由子类自行解析。
        """
        self.sem = sem
        self._default_headers = headers or {}
        self._default_cookies = cookies or {}
        self._verify = verify
        self._engine_options = engine_options

    async def download(self, request: RequestModel) -> Response:
        """发起请求，受信号量控制。

        Args:
            request: 请求模型。

        Returns:
            统一的 Response 响应对象。
        """
        if self.sem:
            async with self.sem:
                return await self._download(request)
        return await self._download(request)

    @property
    @abstractmethod
    def cookies(self) -> dict[str, str]:
        """获取客户端级别的 cookies。

        Returns:
            当前会话的 cookies 字典。
        """
        ...

    @abstractmethod
    async def _download(self, request: RequestModel) -> Response:
        """执行具体的 HTTP 请求，由子类实现。

        Args:
            request: 请求模型。

        Returns:
            统一的 Response 响应对象。
        """
        ...

    @abstractmethod
    async def _stream(self, request: RequestModel) -> StreamResponse:
        """执行流式 HTTP 请求，由子类实现。

        Args:
            request: 请求模型。

        Returns:
            StreamResponse 流式响应对象。
        """
        ...

    async def stream(self, request: RequestModel) -> StreamResponse:
        """发起流式请求，受信号量控制。

        Args:
            request: 请求模型。

        Returns:
            StreamResponse 流式响应对象。
        """
        if self.sem:
            async with self.sem:
                return await self._stream(request)
        return await self._stream(request)

    @abstractmethod
    async def close(self) -> None:
        """关闭引擎，释放底层 HTTP 客户端资源。"""
        ...


class SyncEngineBase(ABC):
    """同步 HTTP 引擎基类，所有同步引擎需实现此接口。"""

    def __init__(
        self,
        sem: ThreadSemaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化同步引擎基类。

        Args:
            sem: 线程信号量，用于控制并发请求数量，为 None 则不限制。
            headers: 默认请求头，会应用到所有请求。
            cookies: 默认 cookies，会应用到所有请求。
            verify: 是否验证 SSL 证书。
            **engine_options: 引擎特定配置，由子类自行解析。
        """
        self.sem = sem
        self._default_headers = headers or {}
        self._default_cookies = cookies or {}
        self._verify = verify
        self._engine_options = engine_options

    def download(self, request: RequestModel) -> Response:
        """发起请求，受信号量控制。

        Args:
            request: 请求模型。

        Returns:
            统一的 Response 响应对象。
        """
        if self.sem:
            with self.sem:
                return self._download(request)
        return self._download(request)

    @property
    @abstractmethod
    def cookies(self) -> dict[str, str]:
        """获取客户端级别的 cookies。

        Returns:
            当前会话的 cookies 字典。
        """
        ...

    @abstractmethod
    def _download(self, request: RequestModel) -> Response:
        """执行具体的 HTTP 请求，由子类实现。

        Args:
            request: 请求模型。

        Returns:
            统一的 Response 响应对象。
        """
        ...

    @abstractmethod
    def _stream(self, request: RequestModel) -> StreamResponse:
        """执行流式 HTTP 请求，由子类实现。

        Args:
            request: 请求模型。

        Returns:
            StreamResponse 流式响应对象。
        """
        ...

    def stream(self, request: RequestModel) -> StreamResponse:
        """发起流式请求，受信号量控制。

        Args:
            request: 请求模型。

        Returns:
            StreamResponse 流式响应对象。
        """
        if self.sem:
            with self.sem:
                return self._stream(request)
        return self._stream(request)

    @abstractmethod
    def close(self) -> None:
        """关闭引擎，释放底层 HTTP 客户端资源。"""
        ...
