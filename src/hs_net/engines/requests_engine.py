from __future__ import annotations

from threading import Semaphore as ThreadSemaphore
from typing import Any

try:
    import requests
    from requests import Session
    from requests.utils import cookiejar_from_dict, dict_from_cookiejar

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

from hs_net.exceptions import ConnectionException, EngineNotInstalled, StatusException, TimeoutException
from hs_net.models import RequestModel
from hs_net.response import Response
from hs_net.response.stream import StreamResponse

from .base import SyncEngineBase, build_proxies_dict, build_response


class SyncRequestsEngine(SyncEngineBase):
    """基于 requests 的同步 HTTP 引擎。"""

    def __init__(
        self,
        sem: ThreadSemaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        **engine_options: Any,
    ):
        """初始化 requests 引擎。

        Args:
            sem: 线程信号量，用于控制并发请求数量。
            headers: 默认请求头。
            cookies: 默认 cookies。
            verify: 是否验证 SSL 证书。
            **engine_options: requests 特定配置。
        """
        if not _HAS_REQUESTS:
            raise EngineNotInstalled("requests", "hs-net[requests]")

        super().__init__(sem, headers, cookies, verify, **engine_options)

        self.client = Session()
        self.client.verify = self._verify

        if not self._verify:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.client.headers.update(self._default_headers)
        self.client.cookies = cookiejar_from_dict(self._default_cookies)

    def close(self):
        """关闭 requests 会话。"""
        self.client.close()

    @property
    def cookies(self) -> dict[str, str]:
        """获取客户端会话 cookies。

        Returns:
            cookies 字典。
        """
        return dict_from_cookiejar(self.client.cookies)

    def _download(self, request_data: RequestModel) -> Response:
        """使用 requests 执行同步 HTTP 请求。

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
            response = self.client.request(
                method=request_data.method,
                url=request_data.url,
                params=request_data.url_params,
                data=request_data.form_data if not request_data.files else None,
                json=request_data.json_data,
                files=request_data.files,
                cookies=request_data.cookies,
                headers=request_data.headers,
                proxies=build_proxies_dict(request_data.proxy),
                timeout=request_data.timeout,
                allow_redirects=request_data.allow_redirects,
            )

            return build_response(
                url=str(response.url),
                status_code=response.status_code,
                headers=dict(response.headers),
                cookies=dict_from_cookiejar(response.cookies),
                client_cookies=self.cookies,
                content=response.content,
                request_data=request_data,
            )
        except requests.Timeout:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None

    def _stream(self, request_data: RequestModel) -> StreamResponse:
        """使用 requests 执行同步流式 HTTP 请求。

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
            response = self.client.request(
                method=request_data.method,
                url=request_data.url,
                params=request_data.url_params,
                data=request_data.form_data if not request_data.files else None,
                json=request_data.json_data,
                files=request_data.files,
                cookies=request_data.cookies,
                headers=request_data.headers,
                proxies=build_proxies_dict(request_data.proxy),
                timeout=request_data.timeout,
                allow_redirects=request_data.allow_redirects,
                stream=True,
            )

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
        except requests.Timeout:
            raise TimeoutException(url=request_data.url, timeout=request_data.timeout) from None
        except requests.ConnectionError as e:
            raise ConnectionException(url=request_data.url, message=str(e)) from None
