"""代理归一化服务测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hs_net.proxy import (
    ApiProxyProvider,
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

    def test_sync_net_with_proxy_string(self):
        """字符串代理也统一走 ProxyService。"""
        from hs_net.sync_client import SyncNet

        net = SyncNet(proxy="http://127.0.0.1:8080", verify=False, retries=0)
        assert net.proxy_service is not None
        assert net.proxy_service.started
        net.close()

    @pytest.mark.asyncio
    async def test_async_net_with_proxy_service(self):
        from hs_net.client import Net

        svc = ProxyService("http://127.0.0.1:8080")
        async with Net(proxy=svc, verify=False, retries=0) as net:
            assert net.proxy_service is svc
            assert svc.started

    @pytest.mark.asyncio
    async def test_async_net_no_proxy(self):
        from hs_net.client import Net

        async with Net(verify=False, retries=0) as net:
            assert net.proxy_service is None


class TestAsyncGetProxy:
    """async_get_proxy 测试。"""

    @pytest.mark.asyncio
    async def test_default_fallback_to_sync(self):
        """默认 async_get_proxy 回退到同步 get_proxy。"""
        provider = FixedProxyProvider("http://proxy:8080")
        result = await provider.async_get_proxy()
        assert result == "http://proxy:8080"

    @pytest.mark.asyncio
    async def test_async_fallback(self):
        provider = ListProxyProvider(["a", "b", "c"])
        assert await provider.async_get_proxy() == "a"
        assert await provider.async_get_proxy() == "b"

    @pytest.mark.asyncio
    async def test_custom_async_override(self):
        """自定义 Provider 可覆写 async_get_proxy。"""

        class AsyncProvider(ProxyProvider):
            def get_proxy(self) -> str:
                return "sync://proxy:1080"

            async def async_get_proxy(self) -> str:
                return "async://proxy:1080"

        provider = AsyncProvider()
        assert provider.get_proxy() == "sync://proxy:1080"
        assert await provider.async_get_proxy() == "async://proxy:1080"


class TestApiProxyProvider:
    """ApiProxyProvider 测试。"""

    def test_sync_get_proxy(self):
        """同步获取代理。"""
        mock_resp = MagicMock()
        mock_resp.text = "  http://1.2.3.4:8080  \n"
        mock_resp.raise_for_status = MagicMock()

        provider = ApiProxyProvider("https://api.pool.com/get")
        with patch.object(provider, "_ensure_sync_client") as mock_client:
            mock_client.return_value.get.return_value = mock_resp
            result = provider.get_proxy()

        assert result == "http://1.2.3.4:8080"

    @pytest.mark.asyncio
    async def test_async_get_proxy(self):
        """异步获取代理。"""
        mock_resp = MagicMock()
        mock_resp.text = "socks5://5.6.7.8:1080"
        mock_resp.raise_for_status = MagicMock()

        provider = ApiProxyProvider("https://api.pool.com/get")
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        with patch.object(provider, "_ensure_async_client", return_value=mock_client):
            result = await provider.async_get_proxy()

        assert result == "socks5://5.6.7.8:1080"

    def test_custom_parser(self):
        """自定义 parser 从 JSON 中提取。"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"proxy": "http://9.8.7.6:3128"}}
        mock_resp.raise_for_status = MagicMock()

        provider = ApiProxyProvider(
            "https://api.pool.com/get",
            parser=lambda resp: resp.json()["data"]["proxy"],
        )
        with patch.object(provider, "_ensure_sync_client") as mock_client:
            mock_client.return_value.get.return_value = mock_resp
            result = provider.get_proxy()

        assert result == "http://9.8.7.6:3128"

    def test_proxy_param_stored(self):
        """proxy 参数正确存储。"""
        provider = ApiProxyProvider(
            "https://api.pool.com/get",
            proxy="http://127.0.0.1:7897",
        )
        assert provider._proxy == "http://127.0.0.1:7897"

    def test_close(self):
        """close 关闭内部客户端。"""
        provider = ApiProxyProvider("https://api.pool.com/get")
        mock_sync = MagicMock()
        provider._sync_client = mock_sync
        provider.close()
        mock_sync.close.assert_called_once()
        assert provider._sync_client is None

    @pytest.mark.asyncio
    async def test_async_close(self):
        """async_close 关闭异步客户端。"""
        provider = ApiProxyProvider("https://api.pool.com/get")
        mock_async = AsyncMock()
        provider._async_client = mock_async
        await provider.async_close()
        mock_async.aclose.assert_called_once()
        assert provider._async_client is None


class TestProxyServiceWithApiProvider:
    """ProxyService + ApiProxyProvider 集成测试。"""

    def test_service_with_api_provider(self):
        """ProxyService 接受 ApiProxyProvider。"""
        provider = ApiProxyProvider("https://api.pool.com/get")
        svc = ProxyService(provider=provider)
        assert svc.provider is provider

    @pytest.mark.asyncio
    async def test_async_start_uses_async_get_proxy(self):
        """async_start 使用 async_get_proxy。"""

        class TrackingProvider(ProxyProvider):
            def __init__(self):
                self.sync_called = False
                self.async_called = False

            def get_proxy(self) -> str:
                self.sync_called = True
                return "http://127.0.0.1:8080"

            async def async_get_proxy(self) -> str:
                self.async_called = True
                return "http://127.0.0.1:8080"

        provider = TrackingProvider()
        svc = ProxyService(provider=provider)
        await svc.async_start()
        try:
            assert provider.async_called
            assert not provider.sync_called
        finally:
            await svc.async_stop()

    @pytest.mark.asyncio
    async def test_async_switch(self):
        """async_switch 使用 async_get_proxy。"""

        class CountingProvider(ProxyProvider):
            def __init__(self):
                self.async_count = 0

            def get_proxy(self) -> str:
                return "http://127.0.0.1:8080"

            async def async_get_proxy(self) -> str:
                self.async_count += 1
                return "http://127.0.0.1:8080"

        provider = CountingProvider()
        svc = ProxyService(provider=provider)
        await svc.async_start()
        try:
            assert provider.async_count == 1  # async_start 调用了一次
            await svc.async_switch()
            assert provider.async_count == 2
        finally:
            await svc.async_stop()
