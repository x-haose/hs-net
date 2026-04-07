"""流式 HTTP 响应对象。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

from hs_net.models import RequestModel


class StreamResponse:
    """流式 HTTP 响应对象，支持分块读取响应体。

    用法（异步）::

        resp = await net.stream("GET", url)
        async with resp:
            async for chunk in resp:
                f.write(chunk)

    用法（同步）::

        with sync_net.stream("GET", url) as resp:
            for chunk in resp:
                f.write(chunk)
    """

    def __init__(
        self,
        url: str,
        status_code: int,
        headers: dict[str, Any],
        cookies: dict[str, str],
        client_cookies: dict[str, str],
        request_data: RequestModel,
        stream: Any,  # The underlying engine stream object
        close_callback: Any = None,  # Callable to close the stream
    ):
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.cookies = cookies
        self.client_cookies = client_cookies
        self.request_data = request_data
        self._stream = stream
        self._close_callback = close_callback

    @property
    def ok(self) -> bool:
        """状态码是否在 2xx 范围内。"""
        return 200 <= self.status_code < 300

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """异步迭代响应体的分块数据。"""
        async for chunk in self._stream:
            yield chunk

    def __iter__(self) -> Iterator[bytes]:
        """同步迭代响应体的分块数据。"""
        yield from self._stream

    async def aclose(self) -> None:
        """关闭流式响应（异步）。"""
        if self._close_callback:
            result = self._close_callback()
            if hasattr(result, "__await__"):
                await result

    def close(self) -> None:
        """关闭流式响应（同步）。"""
        if self._close_callback:
            self._close_callback()

    async def __aenter__(self) -> StreamResponse:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    def __enter__(self) -> StreamResponse:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<StreamResponse [{self.status_code}] {self.url}>"
