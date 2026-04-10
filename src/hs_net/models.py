from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EngineEnum(StrEnum):
    """可用的 HTTP 引擎枚举。

    Attributes:
        HTTPX: httpx 异步引擎，支持 HTTP/2。
        AIOHTTP: aiohttp 异步引擎。
        REQUESTS: requests 同步引擎（不建议在异步场景使用）。
        CURL_CFFI: curl-cffi 引擎，支持浏览器指纹模拟。
        REQUESTS_GO: requests-go 异步引擎，基于 Go 实现。
    """

    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    REQUESTS = "requests"
    CURL_CFFI = "curl_cffi"
    REQUESTS_GO = "requests_go"


@dataclass
class RequestModel:
    """请求模型，封装单次 HTTP 请求的所有参数。

    Attributes:
        url: 请求的目标 URL。
        method: HTTP 请求方法，默认 GET。
        url_params: URL 查询参数。
        form_data: 表单数据，支持 dict、list[tuple]、str、bytes。
        json_data: JSON 请求体数据。
        files: 文件上传数据，格式同 requests/httpx 的 files 参数。
        raise_status: 状态码非 2xx 时是否抛出异常。
        allow_redirects: 是否允许自动重定向。
        verify: 是否验证 SSL 证书。
        user_agent: 请求的 User-Agent。
        headers: 请求头。
        cookies: 请求携带的 cookies。
        timeout: 请求超时时间（秒）。
        proxy:   请求代理。
        retries: 重试次数。
        retry_delay: 重试间隔时间（秒）。
    """

    url: str
    method: str = "GET"
    url_params: dict[str, Any] | None = None
    form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None
    json_data: dict[str, Any] | None = None
    files: dict[str, Any] | list[tuple] | None = None
    raise_status: bool = True
    allow_redirects: bool = True
    verify: bool = True
    user_agent: str | None = None
    headers: dict[str, Any] | None = field(default_factory=dict)
    cookies: dict[str, Any] | None = field(default_factory=dict)
    timeout: float | None = None
    proxy: str | None = None
    retries: int | None = None
    retry_delay: float | None = None
