from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hs_net.models import EngineEnum


@dataclass(frozen=True)
class NetConfig:
    """Net 客户端配置，通过类属性设置全局默认值。

    可直接实例化后传给 Net/SyncNet，也可继承自定义默认值::

        class MyConfig(NetConfig):
            engine = EngineEnum.CURL_CFFI
            retries = 5
            user_agent = "chrome"

        net = Net(config=MyConfig())

    Attributes:
        engine: HTTP 引擎，支持字符串或 EngineEnum 枚举。
        base_url: 基础 URL，请求时自动拼接，如 "https://api.example.com/v1"。
        timeout: 请求超时时间（秒）。
        retries: 请求失败后的重试次数。
        retry_delay: 重试间隔时间（秒），为 0 则立即重试。
        user_agent: User-Agent 配置，支持 "random"、"chrome" 等快捷方式。
        proxy: 全局代理地址。
        verify: 是否验证 SSL 证书，默认开启。
        raise_status: 状态码非 2xx 时是否抛出异常。
        allow_redirects: 是否允许自动重定向。
        concurrency: 最大并发数，为 None 则不限制。
        headers: 全局默认请求头。
        cookies: 全局默认 cookies。
        engine_options: 引擎特定配置，透传给引擎构造函数。
    """

    engine: str | EngineEnum = EngineEnum.HTTPX
    base_url: str = ""
    timeout: float = 20.0
    retries: int = 3
    retry_delay: float = 0.0
    user_agent: str = "random"
    proxy: str | None = None
    verify: bool = True
    raise_status: bool = True
    allow_redirects: bool = True
    concurrency: int | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    cookies: dict[str, Any] = field(default_factory=dict)
    engine_options: dict[str, Any] = field(default_factory=dict)
