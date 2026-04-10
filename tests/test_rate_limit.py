"""速率限制模块测试。"""

from __future__ import annotations

import asyncio
import time

import pytest

from hs_net.config import NetConfig
from hs_net.rate_limit import (
    RateLimitConfig,
    RateLimitManager,
    SyncRateLimitManager,
    _extract_domain,
    _normalize_domain_config,
)


class TestRateLimitConfig:
    """RateLimitConfig 配置测试。"""

    def test_default_values(self):
        config = RateLimitConfig(rate=5)
        assert config.rate == 5
        assert config.duration == 1000
        assert config.per_domain == {}
        assert config.backend is None

    def test_custom_duration(self):
        config = RateLimitConfig(rate=100, duration=60_000)
        assert config.rate == 100
        assert config.duration == 60_000

    def test_per_domain_config(self):
        config = RateLimitConfig(
            rate=10,
            per_domain={
                "api.example.com": 2,
                "slow.example.com": RateLimitConfig(rate=1),
            },
        )
        assert config.per_domain["api.example.com"] == 2
        assert isinstance(config.per_domain["slow.example.com"], RateLimitConfig)

    def test_frozen(self):
        config = RateLimitConfig(rate=5)
        with pytest.raises(AttributeError):
            config.rate = 10


class TestHelpers:
    """辅助函数测试。"""

    def test_extract_domain(self):
        assert _extract_domain("https://api.example.com/v1/users") == "api.example.com"
        assert _extract_domain("http://localhost:8080/test") == "localhost"
        assert _extract_domain("https://example.com") == "example.com"

    def test_extract_domain_empty(self):
        assert _extract_domain("") == ""

    def test_normalize_int(self):
        result = _normalize_domain_config(5)
        assert isinstance(result, RateLimitConfig)
        assert result.rate == 5

    def test_normalize_float(self):
        result = _normalize_domain_config(3.5)
        assert isinstance(result, RateLimitConfig)
        assert result.rate == 3

    def test_normalize_config_passthrough(self):
        config = RateLimitConfig(rate=10, duration=5000)
        result = _normalize_domain_config(config)
        assert result is config


class TestSyncRateLimitManager:
    """同步限速管理器测试。"""

    def test_global_rate_limit(self):
        """全局限速应正常工作。"""
        manager = SyncRateLimitManager(RateLimitConfig(rate=5))
        # 前 5 个应立即通过
        start = time.monotonic()
        for _ in range(5):
            manager.acquire("https://example.com/page")
        elapsed = time.monotonic() - start
        assert elapsed < 0.2

    def test_global_rate_limit_blocks(self):
        """超出限速后应阻塞等待。"""
        manager = SyncRateLimitManager(RateLimitConfig(rate=3))
        for _ in range(3):
            manager.acquire("https://example.com/page")
        start = time.monotonic()
        manager.acquire("https://example.com/page")
        elapsed = time.monotonic() - start
        # 第 4 个请求应等待约 0.3s (1/3)
        assert elapsed >= 0.2

    def test_domain_priority(self):
        """域名配置应优先于全局，互相独立。"""
        manager = SyncRateLimitManager(
            RateLimitConfig(
                rate=100,
                per_domain={"slow.example.com": 2},
            )
        )
        # slow.example.com 限速为 2/s，发 2 个后第 3 个应等待
        manager.acquire("https://slow.example.com/a")
        manager.acquire("https://slow.example.com/b")
        start = time.monotonic()
        manager.acquire("https://slow.example.com/c")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3

    def test_unmatched_domain_uses_global(self):
        """未匹配域名应使用全局限速器。"""
        manager = SyncRateLimitManager(
            RateLimitConfig(
                rate=3,
                per_domain={"slow.example.com": 1},
            )
        )
        # other.com 用全局限速 3/s
        for _ in range(3):
            manager.acquire("https://other.com/page")
        start = time.monotonic()
        manager.acquire("https://other.com/page")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.2

    def test_no_rate_no_global_limiter(self):
        """rate=0 时不创建全局限速器。"""
        manager = SyncRateLimitManager(RateLimitConfig(rate=0, per_domain={"api.example.com": 5}))
        assert manager._global_limiter is None

    def test_only_per_domain(self):
        """只配域名不配全局，非匹配域名不限速。"""
        manager = SyncRateLimitManager(RateLimitConfig(rate=0, per_domain={"api.example.com": 3}))
        start = time.monotonic()
        for _ in range(20):
            manager.acquire("https://other.com/page")
        elapsed = time.monotonic() - start
        assert elapsed < 0.2


class TestAsyncRateLimitManager:
    """异步限速管理器测试。"""

    @pytest.mark.asyncio
    async def test_global_rate_limit(self):
        manager = RateLimitManager(RateLimitConfig(rate=5))
        start = time.monotonic()
        for _ in range(5):
            await manager.acquire("https://example.com/page")
        elapsed = time.monotonic() - start
        assert elapsed < 0.2

    @pytest.mark.asyncio
    async def test_global_rate_limit_blocks(self):
        manager = RateLimitManager(RateLimitConfig(rate=3))
        for _ in range(3):
            await manager.acquire("https://example.com/page")
        start = time.monotonic()
        await manager.acquire("https://example.com/page")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.2

    @pytest.mark.asyncio
    async def test_domain_priority(self):
        manager = RateLimitManager(
            RateLimitConfig(
                rate=100,
                per_domain={"slow.example.com": 2},
            )
        )
        await manager.acquire("https://slow.example.com/a")
        await manager.acquire("https://slow.example.com/b")
        start = time.monotonic()
        await manager.acquire("https://slow.example.com/c")
        elapsed = time.monotonic() - start
        assert elapsed >= 0.3

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """并发请求应被正确限速。"""
        manager = RateLimitManager(RateLimitConfig(rate=3))

        async def do_acquire():
            await manager.acquire("https://example.com/page")

        start = time.monotonic()
        await asyncio.gather(*[do_acquire() for _ in range(6)])
        elapsed = time.monotonic() - start
        # 3/s，6 个请求至少需要 ~1s
        assert elapsed >= 0.8


class TestCustomBackend:
    """自定义后端测试。"""

    def test_custom_backend_sync(self):
        """自定义桶实例应被直接使用。"""
        from pyrate_limiter import InMemoryBucket, Rate

        custom_bucket = InMemoryBucket([Rate(10, 1000)])
        config = RateLimitConfig(rate=10, backend=custom_bucket)
        manager = SyncRateLimitManager(config)
        manager.acquire("https://example.com/test")

    @pytest.mark.asyncio
    async def test_custom_backend_async(self):
        """异步模式下自定义桶实例应被直接使用。"""
        from pyrate_limiter import BucketAsyncWrapper, InMemoryBucket, Rate

        custom_bucket = BucketAsyncWrapper(InMemoryBucket([Rate(10, 1000)]))
        config = RateLimitConfig(rate=10, backend=custom_bucket)
        manager = RateLimitManager(config)
        await manager.acquire("https://example.com/test")

    def test_redis_bucket_importable(self):
        """RedisBucket 类应可导入（即使 redis 包未安装）。"""
        from pyrate_limiter import RedisBucket

        assert RedisBucket is not None

    def test_no_pyrate_limiter_raises(self):
        """未安装 pyrate-limiter 时应抛出友好异常。"""
        import sys
        import unittest.mock

        with unittest.mock.patch.dict(sys.modules, {"pyrate_limiter": None}):
            from hs_net.exceptions import RequestException
            from hs_net.rate_limit import _check_installed

            with pytest.raises(RequestException, match="速率限制需要额外安装依赖"):
                _check_installed()


class TestNetConfigIntegration:
    """NetConfig 集成测试。"""

    def test_config_with_int(self):
        config = NetConfig(rate_limit=5)
        assert config.rate_limit == 5

    def test_config_with_rate_limit_config(self):
        rl = RateLimitConfig(rate=10, per_domain={"a.com": 2})
        config = NetConfig(rate_limit=rl)
        assert config.rate_limit is rl

    def test_config_default_none(self):
        config = NetConfig()
        assert config.rate_limit is None

    def test_merge_config_override(self):
        from hs_net._shared import merge_config

        config = NetConfig(rate_limit=10)
        merged = merge_config(config, rate_limit=5)
        assert merged.rate_limit == 5

    def test_merge_config_inherit(self):
        from hs_net._shared import merge_config

        config = NetConfig(rate_limit=10)
        merged = merge_config(config)
        assert merged.rate_limit == 10


class TestClientIntegration:
    """客户端集成测试。"""

    @pytest.mark.asyncio
    async def test_net_with_rate_limit_int(self):
        from hs_net.client import Net

        async with Net(rate_limit=5) as net:
            assert net._rate_limiter is not None

    @pytest.mark.asyncio
    async def test_net_with_rate_limit_config(self):
        from hs_net.client import Net

        async with Net(rate_limit=RateLimitConfig(rate=5, per_domain={"a.com": 2})) as net:
            assert net._rate_limiter is not None

    @pytest.mark.asyncio
    async def test_net_no_rate_limit(self):
        from hs_net.client import Net

        async with Net() as net:
            assert net._rate_limiter is None

    def test_sync_net_with_rate_limit(self):
        from hs_net.sync_client import SyncNet

        net = SyncNet(rate_limit=5)
        assert net._rate_limiter is not None
        net.close()

    def test_sync_net_no_rate_limit(self):
        from hs_net.sync_client import SyncNet

        net = SyncNet()
        assert net._rate_limiter is None
        net.close()

    def test_sync_net_via_config(self):
        from hs_net.sync_client import SyncNet

        config = NetConfig(rate_limit=RateLimitConfig(rate=3))
        net = SyncNet(config=config)
        assert net._rate_limiter is not None
        net.close()
