"""代理归一化服务测试。"""

from __future__ import annotations

import pytest

from hs_net.proxy import (
    FixedProxyProvider,
    ListProxyProvider,
    ProxyProvider,
    ProxyService,
    _parse_proxy,
)


class TestParseProxy:
    """代理 URL 解析测试。"""

    def test_http_proxy(self):
        info = _parse_proxy("http://192.168.1.1:8080")
        assert info.scheme == "http"
        assert info.host == "192.168.1.1"
        assert info.port == 8080
        assert info.username is None
        assert info.password is None

    def test_socks5_proxy(self):
        info = _parse_proxy("socks5://10.0.0.1:1080")
        assert info.scheme == "socks5"
        assert info.host == "10.0.0.1"
        assert info.port == 1080

    def test_auth_proxy(self):
        info = _parse_proxy("http://user:pass123@proxy.example.com:3128")
        assert info.scheme == "http"
        assert info.host == "proxy.example.com"
        assert info.port == 3128
        assert info.username == "user"
        assert info.password == "pass123"

    def test_socks5_with_auth(self):
        info = _parse_proxy("socks5://admin:secret@10.0.0.1:1080")
        assert info.scheme == "socks5"
        assert info.username == "admin"
        assert info.password == "secret"

    def test_default_port_http(self):
        info = _parse_proxy("http://proxy.com")
        assert info.port == 8080

    def test_default_port_socks(self):
        info = _parse_proxy("socks5://proxy.com")
        assert info.port == 1080

    def test_invalid_proxy_raises(self):
        with pytest.raises(ValueError, match="无法解析代理地址"):
            _parse_proxy("proxy.com")


class TestFixedProxyProvider:
    """固定代理提供者测试。"""

    def test_always_returns_same(self):
        provider = FixedProxyProvider("http://proxy:8080")
        assert provider.get_proxy() == "http://proxy:8080"
        assert provider.get_proxy() == "http://proxy:8080"


class TestListProxyProvider:
    """列表代理提供者测试。"""

    def test_round_robin(self):
        provider = ListProxyProvider(["a", "b", "c"], strategy="round_robin")
        assert provider.get_proxy() == "a"
        assert provider.get_proxy() == "b"
        assert provider.get_proxy() == "c"
        assert provider.get_proxy() == "a"

    def test_random(self):
        provider = ListProxyProvider(["a", "b", "c"], strategy="random")
        results = {provider.get_proxy() for _ in range(100)}
        # 随机 100 次应该覆盖到所有选项
        assert results == {"a", "b", "c"}

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="代理列表不能为空"):
            ListProxyProvider([])


class TestCustomProvider:
    """自定义代理提供者测试。"""

    def test_custom_implementation(self):
        class CountingProvider(ProxyProvider):
            def __init__(self):
                self._count = 0

            def get_proxy(self) -> str:
                self._count += 1
                return f"http://proxy{self._count}:8080"

        provider = CountingProvider()
        assert provider.get_proxy() == "http://proxy1:8080"
        assert provider.get_proxy() == "http://proxy2:8080"


class TestProxyServiceInit:
    """ProxyService 初始化测试。"""

    def test_from_string(self):
        svc = ProxyService("http://proxy:8080")
        assert isinstance(svc.provider, FixedProxyProvider)

    def test_from_list(self):
        svc = ProxyService(["http://p1:8080", "http://p2:8080"])
        assert isinstance(svc.provider, ListProxyProvider)

    def test_from_provider(self):
        provider = FixedProxyProvider("http://proxy:8080")
        svc = ProxyService(provider=provider)
        assert svc.provider is provider

    def test_no_args_raises(self):
        with pytest.raises(ValueError, match="必须提供"):
            ProxyService()

    def test_not_started(self):
        svc = ProxyService("http://proxy:8080")
        assert not svc.started
        with pytest.raises(RuntimeError, match="尚未启动"):
            _ = svc.local_url


class TestProxyServiceSync:
    """ProxyService 同步启停测试。"""

    def test_start_stop(self):
        svc = ProxyService("http://127.0.0.1:8080")
        svc.start()
        assert svc.started
        assert svc.local_url.startswith("http://127.0.0.1:")
        port = int(svc.local_url.split(":")[-1])
        assert port > 0
        svc.stop()
        assert not svc.started

    def test_switch(self):
        svc = ProxyService(["http://p1:8080", "http://p2:8080"])
        svc.start()
        try:
            url1 = svc.local_url
            svc.switch()
            url2 = svc.local_url
            # 端口不变，只是上游切了
            assert url1 == url2
        finally:
            svc.stop()

    def test_double_start(self):
        svc = ProxyService("http://127.0.0.1:8080")
        svc.start()
        svc.start()  # 不应该报错
        assert svc.started
        svc.stop()

    def test_double_stop(self):
        svc = ProxyService("http://127.0.0.1:8080")
        svc.start()
        svc.stop()
        svc.stop()  # 不应该报错


class TestProxyServiceAsync:
    """ProxyService 异步启停测试。"""

    @pytest.mark.asyncio
    async def test_async_start_stop(self):
        svc = ProxyService("http://127.0.0.1:8080")
        await svc.async_start()
        assert svc.started
        assert svc.local_url.startswith("http://127.0.0.1:")
        await svc.async_stop()
        assert not svc.started


class TestClientIntegration:
    """客户端集成测试。"""

    def test_sync_net_with_proxy_service(self):
        from hs_net.sync_client import SyncNet

        svc = ProxyService("http://127.0.0.1:8080")
        net = SyncNet(proxy=svc, verify=False, retries=0)
        assert net.proxy_service is svc
        assert svc.started
        net.close()

    def test_sync_net_with_proxy_list(self):
        from hs_net.sync_client import SyncNet

        net = SyncNet(proxy=["http://p1:8080", "http://p2:8080"], verify=False, retries=0)
        assert net.proxy_service is not None
        assert net.proxy_service.started
        net.close()

    def test_sync_net_with_proxy_string(self):
        """字符串代理走传统路径，不创建 ProxyService。"""
        from hs_net.sync_client import SyncNet

        net = SyncNet(proxy="http://127.0.0.1:8080", verify=False, retries=0)
        assert net.proxy_service is None
        net.close()

    @pytest.mark.asyncio
    async def test_async_net_with_proxy_service(self):
        from hs_net.client import Net

        svc = ProxyService("http://127.0.0.1:8080")
        async with Net(proxy=svc, verify=False, retries=0) as net:
            assert net.proxy_service is svc
            assert svc.started

    @pytest.mark.asyncio
    async def test_async_net_with_proxy_list(self):
        from hs_net.client import Net

        async with Net(proxy=["http://p1:8080", "http://p2:8080"], verify=False, retries=0) as net:
            assert net.proxy_service is not None
            assert net.proxy_service.started

    @pytest.mark.asyncio
    async def test_async_net_no_proxy(self):
        from hs_net.client import Net

        async with Net(verify=False, retries=0) as net:
            assert net.proxy_service is None
