from __future__ import annotations

from typing import Any

from tenacity import Future, RetryCallState

from hs_net.config import NetConfig
from hs_net.exceptions import StatusException


def merge_config(
    config: NetConfig | None,
    *,
    engine=None,
    base_url=None,
    timeout=None,
    retries=None,
    retry_delay=None,
    user_agent=None,
    proxy=None,
    verify=None,
    raise_status=None,
    allow_redirects=None,
    rate_limit=None,
    concurrency=None,
    headers: dict[str, Any] | None = None,
    cookies: dict[str, Any] | None = None,
    engine_options: dict[str, Any] | None = None,
) -> NetConfig:
    """合并构造函数参数与配置对象，构造函数参数优先。"""
    cfg = config or NetConfig()
    return NetConfig(
        engine=engine or cfg.engine,
        base_url=base_url if base_url is not None else cfg.base_url,
        timeout=timeout if timeout is not None else cfg.timeout,
        retries=retries if retries is not None else cfg.retries,
        retry_delay=retry_delay if retry_delay is not None else cfg.retry_delay,
        user_agent=user_agent or cfg.user_agent,
        proxy=proxy if proxy is not None else cfg.proxy,
        verify=verify if verify is not None else cfg.verify,
        raise_status=raise_status if raise_status is not None else cfg.raise_status,
        allow_redirects=allow_redirects if allow_redirects is not None else cfg.allow_redirects,
        rate_limit=rate_limit if rate_limit is not None else cfg.rate_limit,
        concurrency=concurrency if concurrency is not None else cfg.concurrency,
        headers={**cfg.headers, **(headers or {})},
        cookies={**cfg.cookies, **(cookies or {})},
        engine_options={**cfg.engine_options, **(engine_options or {})},
    )


def format_retry_log(req_data, retry_state: RetryCallState) -> tuple[str, int, Exception]:
    """提取重试信息用于日志记录。

    Returns:
        (log_msg, attempt, exception) 元组。
    """
    outcome: Future = retry_state.outcome
    attempt = retry_state.attempt_number
    exception = outcome.exception()
    exc_type = type(exception).__name__
    exc_msg = str(exception)

    if isinstance(exception, StatusException):
        exc_msg = f"HTTP {exception.code}"

    log_msg = f"[{req_data.method}] {req_data.url} error=[{exc_type}]: {exc_msg}"
    return log_msg, attempt, exception
