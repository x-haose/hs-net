"""公共请求构建逻辑，供 Net 和 SyncNet 共享。"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from hs_net.config import NetConfig
from hs_net.models import RequestModel
from hs_net.ua import resolve_user_agent


def build_request(
    cfg: NetConfig,
    url: str,
    method: str,
    *,
    params: dict = None,
    json_data: dict = None,
    form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None,
    files: dict[str, Any] | list[tuple] | None = None,
    user_agent: str = None,
    headers: dict = None,
    cookies: dict = None,
    timeout: float = None,
    verify: bool = None,
    retries: int = None,
    retry_delay: float = None,
    raise_status: bool = None,
    allow_redirects: bool = None,
) -> RequestModel:
    """构建请求模型，方法参数覆盖实例配置。

    Args:
        cfg: 客户端配置。
        url: 请求目标 URL。
        method: HTTP 请求方法。
        params: URL 查询参数。
        json_data: JSON 请求体。
        form_data: 表单数据，支持 dict、list[tuple]、str、bytes。
        files: 文件上传数据。
        user_agent: User-Agent，覆盖实例配置。
        headers: 请求头，与实例配置合并。
        cookies: cookies，与实例配置合并。
        timeout: 超时时间（秒），覆盖实例配置。
        verify: 是否验证 SSL 证书，覆盖实例配置。
        retries: 重试次数，覆盖实例配置。
        retry_delay: 重试间隔（秒），覆盖实例配置。
        raise_status: 是否抛出状态码异常，覆盖实例配置。
        allow_redirects: 是否允许重定向，覆盖实例配置。

    Returns:
        构建好的 RequestModel 实例。
    """
    # base_url 拼接
    if cfg.base_url and not url.startswith(("http://", "https://")):
        base = cfg.base_url.rstrip("/")
        path = url if url.startswith("/") else f"/{url}"
        url = f"{base}{path}"

    ua = resolve_user_agent(user_agent or cfg.user_agent)
    req_headers = {**cfg.headers, **(headers or {})}
    if ua:
        req_headers["User-Agent"] = ua

    # form 编码处理（不和 files 冲突）
    if form_data and not files and isinstance(form_data, list | dict):
        form_data = urlencode(form_data, doseq=True)
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"

    return RequestModel(
        url=url,
        method=method,
        url_params=params,
        json_data=json_data,
        form_data=form_data,
        files=files,
        user_agent=ua,
        headers=req_headers,
        cookies={**cfg.cookies, **(cookies or {})},
        timeout=timeout if timeout is not None else cfg.timeout,
        verify=verify if verify is not None else cfg.verify,
        retries=retries if retries is not None else cfg.retries,
        retry_delay=retry_delay if retry_delay is not None else cfg.retry_delay,
        raise_status=raise_status if raise_status is not None else cfg.raise_status,
        allow_redirects=allow_redirects if allow_redirects is not None else cfg.allow_redirects,
    )
