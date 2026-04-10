"""速率限制模块，基于 pyrate-limiter 实现令牌桶限流。

支持全局限速和按域名独立限速，同步异步双模式。

用法::

    # 简单全局限速
    net = Net(rate_limit=5)

    # 按域名配置
    net = Net(rate_limit=RateLimitConfig(
        rate=10,
        per_domain={
            "api.example.com": 2,
            "slow.example.com": RateLimitConfig(rate=1),
        },
    ))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


def _check_installed() -> None:
    """检查 pyrate-limiter 是否已安装。"""
    try:
        import pyrate_limiter  # noqa: F401
    except ImportError:
        from hs_net.exceptions import RequestException

        raise RequestException(
            "RateLimitNotInstalled",
            "速率限制需要额外安装依赖: pip install hs-net[sp]",
        ) from None


@dataclass(frozen=True)
class RateLimitConfig:
    """速率限制配置。

    Attributes:
        rate: 时间窗口内允许的请求数。
        duration: 时间窗口（毫秒），默认 1000（1 秒）。
            可使用 pyrate_limiter.Duration 常量。
        per_domain: 域名级别覆盖配置，值为 int/float 或 RateLimitConfig。
        backend: 自定义桶实例（如 RedisBucket），为 None 时使用内存桶。
    """

    rate: int = 0
    duration: int = 1000
    per_domain: dict[str, int | float | RateLimitConfig] = field(default_factory=dict)
    backend: Any = None


def _make_rates(config: RateLimitConfig) -> list:
    """根据配置构建 Rate 列表。"""
    from pyrate_limiter import Rate

    return [Rate(config.rate, config.duration)]


def _make_bucket(config: RateLimitConfig, *, async_mode: bool = False):
    """根据配置构建桶实例。"""
    from pyrate_limiter import BucketAsyncWrapper, InMemoryBucket

    if config.backend is not None:
        return config.backend

    rates = _make_rates(config)
    bucket = InMemoryBucket(rates)
    if async_mode:
        bucket = BucketAsyncWrapper(bucket)
    return bucket


def _normalize_domain_config(value: int | float | RateLimitConfig) -> RateLimitConfig:
    """将域名配置归一化为 RateLimitConfig。"""
    if isinstance(value, int | float):
        return RateLimitConfig(rate=int(value))
    return value


def _extract_domain(url: str) -> str:
    """从 URL 中提取域名。"""
    parsed = urlparse(url)
    return parsed.hostname or ""


class RateLimitManager:
    """异步速率限制管理器。

    管理全局限速器和按域名独立的限速器。
    Limiter 延迟到首次 acquire 时创建，避免在无事件循环上下文中报错。
    """

    def __init__(self, config: RateLimitConfig):
        _check_installed()
        self._config = config
        self._initialized = False
        self._global_limiter = None
        self._domain_limiters: dict = {}

    def _ensure_initialized(self) -> None:
        """首次调用时初始化 Limiter（需要在事件循环内）。"""
        if self._initialized:
            return
        self._initialized = True
        from pyrate_limiter import Limiter

        if self._config.rate > 0:
            bucket = _make_bucket(self._config, async_mode=True)
            self._global_limiter = Limiter(bucket)

        for domain, domain_cfg in self._config.per_domain.items():
            normalized = _normalize_domain_config(domain_cfg)
            bucket = _make_bucket(normalized, async_mode=True)
            self._domain_limiters[domain] = Limiter(bucket)

    async def acquire(self, url: str) -> None:
        """获取令牌，超限时异步阻塞等待。"""
        self._ensure_initialized()
        domain = _extract_domain(url)

        # 域名优先，命中则只用域名限速器
        if domain in self._domain_limiters:
            await self._domain_limiters[domain].try_acquire(domain)
            return

        # 未命中则用全局
        if self._global_limiter:
            await self._global_limiter.try_acquire(domain)


class SyncRateLimitManager:
    """同步速率限制管理器。

    管理全局限速器和按域名独立的限速器。
    """

    def __init__(self, config: RateLimitConfig):
        _check_installed()
        from pyrate_limiter import Limiter

        self._config = config

        # 全局限速器
        self._global_limiter: Limiter | None = None
        if config.rate > 0:
            bucket = _make_bucket(config, async_mode=False)
            self._global_limiter = Limiter(bucket)

        # 域名限速器
        self._domain_limiters: dict[str, Limiter] = {}
        for domain, domain_cfg in config.per_domain.items():
            normalized = _normalize_domain_config(domain_cfg)
            bucket = _make_bucket(normalized, async_mode=False)
            self._domain_limiters[domain] = Limiter(bucket)

    def acquire(self, url: str) -> None:
        """获取令牌，超限时阻塞等待。"""
        domain = _extract_domain(url)

        if domain in self._domain_limiters:
            self._domain_limiters[domain].try_acquire(domain)
            return

        if self._global_limiter:
            self._global_limiter.try_acquire(domain)
