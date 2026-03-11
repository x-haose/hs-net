from __future__ import annotations

from json import JSONDecodeError
from threading import Semaphore as ThreadSemaphore
from typing import Any

from requests import Session
from requests.utils import cookiejar_from_dict, dict_from_cookiejar

from hs_net.exceptions import StatusException
from hs_net.models import RequestModel
from hs_net.response import Response

from .base import SyncEngineBase


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
        super().__init__(sem, headers, cookies, verify, **engine_options)

        self.client = Session()
        self.client.verify = self._verify
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
        """
        proxies = {"https": request_data.proxy, "http": request_data.proxy} if request_data.proxy else None

        response = self.client.request(
            method=request_data.method,
            url=request_data.url,
            params=request_data.url_params,
            data=request_data.form_data if not request_data.files else None,
            json=request_data.json_data,
            files=request_data.files,
            cookies=request_data.cookies,
            headers=request_data.headers,
            proxies=proxies,
            timeout=request_data.timeout,
            allow_redirects=request_data.allow_redirects,
        )

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
            client_cookies=self.cookies,
            content=response.content,
            text=response.text,
            json_data=resp_json,
            request_data=request_data,
        )
