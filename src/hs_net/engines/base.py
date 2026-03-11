from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Semaphore
from threading import Semaphore as ThreadSemaphore
from typing import Any

from hs_net.models import RequestModel
from hs_net.response import Response


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
            self.sem.acquire()
            try:
                return self._download(request)
            finally:
                self.sem.release()
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
    def close(self) -> None:
        """关闭引擎，释放底层 HTTP 客户端资源。"""
        ...
