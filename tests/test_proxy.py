"""代理归一化服务测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hs_net.models import RequestModel
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


class TestDomainMatch:
    """域名规则匹配测试。"""

    def test_exact_match(self):
        from hs_net.proxy import _match_domain

        rules = [("github.com", "hit")]
        assert _match_domain("github.com", rules) == "hit"

    def test_wildcard_match(self):
        from hs_net.proxy import _match_domain

        rules = [("*.google.com", "hit")]
        assert _match_domain("www.google.com", rules) == "hit"
        assert _match_domain("mail.google.com", rules) == "hit"

    def test_tld_wildcard(self):
        from hs_net.proxy import _match_domain

        rules = [("*.cn", "hit")]
        assert _match_domain("baidu.cn", rules) == "hit"
        assert _match_domain("www.baidu.cn", rules) == "hit"

    def test_no_match_returns_none(self):
        from hs_net.proxy import _match_domain

        rules = [("github.com", "hit")]
        assert _match_domain("google.com", rules) is None

    def test_first_match_wins(self):
        from hs_net.proxy import _match_domain

        rules = [("*.com", "first"), ("github.com", "second")]
        assert _match_domain("github.com", rules) == "first"

    def test_empty_rules(self):
        from hs_net.proxy import _match_domain

        assert _match_domain("github.com", []) is None

    def test_direct_sentinel(self):
        from hs_net.proxy import DIRECT, _match_domain

        rules = [("*.cn", DIRECT)]
        result = _match_domain("baidu.cn", rules)
        assert result is DIRECT
        assert repr(result) == "DIRECT"


class TestProxyServerRules:
    """_ProxyServer 域名路由测试。"""

    def test_resolve_upstream_exact(self):
        from hs_net.proxy import DIRECT, _parse_proxy, _ProxyServer

        server = _ProxyServer()
        server.set_rules(
            [
                ("github.com", _parse_proxy("http://proxy1:8080")),
                ("*.cn", DIRECT),
            ]
        )
        server.set_upstream(_parse_proxy("http://default:8080"))

        result = server._resolve_upstream("github.com")
        assert result.host == "proxy1"

    def test_resolve_upstream_direct(self):
        from hs_net.proxy import DIRECT, _parse_proxy, _ProxyServer

        server = _ProxyServer()
        server.set_rules([("*.cn", DIRECT)])
        server.set_upstream(_parse_proxy("http://default:8080"))

        result = server._resolve_upstream("baidu.cn")
        assert result is DIRECT

    def test_resolve_upstream_fallback(self):
        from hs_net.proxy import _parse_proxy, _ProxyServer

        server = _ProxyServer()
        server.set_rules([("github.com", _parse_proxy("http://proxy1:8080"))])
        server.set_upstream(_parse_proxy("http://default:8080"))

        result = server._resolve_upstream("google.com")
        assert result.host == "default"

    def test_resolve_upstream_no_rules(self):
        from hs_net.proxy import _parse_proxy, _ProxyServer

        server = _ProxyServer()
        server.set_upstream(_parse_proxy("http://default:8080"))

        result = server._resolve_upstream("anything.com")
        assert result.host == "default"


class TestProxyServiceRules:
    """ProxyService 域名路由规则测试。"""

    def test_rules_param(self):
        svc = ProxyService(
            "http://default:8080",
            rules={"*.cn": "direct", "github.com": "http://proxy1:8080"},
        )
        assert svc.started is False

    def test_rules_sync_start(self):
        svc = ProxyService(
            "http://127.0.0.1:8080",
            rules={"*.cn": "direct"},
        )
        svc.start()
        assert svc.started
        svc.stop()

    @pytest.mark.asyncio
    async def test_rules_async_start(self):
        svc = ProxyService(
            "http://127.0.0.1:8080",
            rules={"*.cn": "direct"},
        )
        await svc.async_start()
        assert svc.started
        await svc.async_stop()

    def test_rules_none_by_default(self):
        """不传 rules 时行为不变。"""
        svc = ProxyService("http://127.0.0.1:8080")
        svc.start()
        assert svc.started
        svc.stop()

    def test_rules_parsed_correctly(self):
        """rules 内部正确解析为 _ProxyInfo 和 DIRECT。"""
        from hs_net.proxy import DIRECT, _ProxyInfo

        svc = ProxyService(
            "http://default:8080",
            rules={
                "*.cn": "direct",
                "github.com": "socks5://proxy1:1080",
            },
        )
        assert len(svc._rules) == 2
        assert svc._rules[0] == ("*.cn", DIRECT)
        pattern, info = svc._rules[1]
        assert pattern == "github.com"
        assert isinstance(info, _ProxyInfo)
        assert info.scheme == "socks5"
        assert info.host == "proxy1"


# ===========================================================================
# 身份路由测试
# ===========================================================================


class TestIdentityExtractor:
    """身份路由 identity_extractor 测试。"""

    def _make_request(self, cookies=None, headers=None, url_params=None):
        return RequestModel(
            url="https://example.com",
            cookies=cookies or {},
            headers=headers or {},
            url_params=url_params,
        )

    def test_no_identity_extractor(self):
        """未配置 identity_extractor 时行为不变。"""
        svc = ProxyService("http://127.0.0.1:8080")
        svc.start()
        assert svc.identity_extractor is None
        svc.stop()

    def test_identity_extractor_property(self):
        """identity_extractor 属性正确返回。"""
        extractor = lambda req: req.cookies.get("sid")  # noqa: E731
        svc = ProxyService("http://127.0.0.1:8080", identity_extractor=extractor)
        assert svc.identity_extractor is extractor

    async def test_resolve_without_extractor(self):
        """无 identity_extractor 时 resolve 返回基础 local_url。"""
        svc = ProxyService("http://127.0.0.1:8080")
        await svc.async_start()
        try:
            req = self._make_request()
            url = await svc.resolve(req)
            assert url == svc.local_url
        finally:
            await svc.async_stop()

    async def test_resolve_extractor_returns_none(self):
        """identity_extractor 返回 None 时走默认代理。"""
        extractor = lambda req: None  # noqa: E731
        svc = ProxyService("http://127.0.0.1:8080", identity_extractor=extractor)
        await svc.async_start()
        try:
            req = self._make_request()
            url = await svc.resolve(req)
            assert url == svc.local_url
        finally:
            await svc.async_stop()

    async def test_resolve_sticky_binding(self):
        """同一身份始终返回相同代理 URL（sticky）。"""
        proxies = iter(["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"])

        class SeqProvider(ProxyProvider):
            def get_proxy(self):
                return next(proxies)

            async def async_get_proxy(self):
                return next(proxies)

        extractor = lambda req: req.cookies.get("sid")  # noqa: E731
        svc = ProxyService(provider=SeqProvider(), identity_extractor=extractor)
        await svc.async_start()
        try:
            req_a1 = self._make_request(cookies={"sid": "aaa"})
            req_a2 = self._make_request(cookies={"sid": "aaa"})
            req_b = self._make_request(cookies={"sid": "bbb"})

            url_a1 = await svc.resolve(req_a1)
            url_a2 = await svc.resolve(req_a2)
            url_b = await svc.resolve(req_b)

            # 同一身份返回相同 URL
            assert url_a1 == url_a2
            # 不同身份返回不同 URL
            assert url_a1 != url_b
            # 都包含 identity hash
            assert "@127.0.0.1:" in url_a1
            assert "@127.0.0.1:" in url_b
        finally:
            await svc.async_stop()

    async def test_resolve_proxy_auth_bridge(self):
        """resolve 返回的 URL 包含正确的 identity_hash。"""
        import hashlib

        extractor = lambda req: req.cookies.get("sid")  # noqa: E731
        svc = ProxyService("http://127.0.0.1:8080", identity_extractor=extractor)
        await svc.async_start()
        try:
            req = self._make_request(cookies={"sid": "test_identity"})
            url = await svc.resolve(req)

            expected_hash = hashlib.md5(b"test_identity").hexdigest()  # noqa: S324
            assert expected_hash in url
            assert url.startswith(f"http://{expected_hash}:x@127.0.0.1:")
        finally:
            await svc.async_stop()

    async def test_identity_from_headers(self):
        """从 headers 提取身份。"""
        extractor = lambda req: req.headers.get("Authorization")  # noqa: E731
        svc = ProxyService("http://127.0.0.1:8080", identity_extractor=extractor)
        await svc.async_start()
        try:
            req = self._make_request(headers={"Authorization": "Bearer token_abc"})
            url = await svc.resolve(req)
            assert "@127.0.0.1:" in url
        finally:
            await svc.async_stop()

    async def test_identity_from_url_params(self):
        """从 URL 参数提取身份。"""
        extractor = lambda req: (req.url_params or {}).get("token")  # noqa: E731
        svc = ProxyService("http://127.0.0.1:8080", identity_extractor=extractor)
        await svc.async_start()
        try:
            req = self._make_request(url_params={"token": "my_token"})
            url = await svc.resolve(req)
            assert "@127.0.0.1:" in url
        finally:
            await svc.async_stop()


class TestProxyServerIdentity:
    """_ProxyServer 身份上游测试。"""

    def test_register_and_resolve(self):
        """注册身份后 _resolve_upstream 返回对应上游。"""
        from hs_net.proxy import _ProxyInfo, _ProxyServer

        server = _ProxyServer()
        default_info = _ProxyInfo(scheme="http", host="default", port=8080, username=None, password=None)
        identity_info = _ProxyInfo(scheme="socks5", host="identity-proxy", port=1080, username=None, password=None)
        server.set_upstream(default_info)
        server.register_identity("abc123", identity_info)

        # 有身份 → 返回身份上游
        result = server._resolve_upstream("example.com", identity_hash="abc123")
        assert result == identity_info

        # 无身份 → 返回默认上游
        result = server._resolve_upstream("example.com")
        assert result == default_info

        # 未注册的身份 → 返回默认上游
        result = server._resolve_upstream("example.com", identity_hash="unknown")
        assert result == default_info

    def test_domain_rules_override_identity(self):
        """域名路由优先于身份路由。"""
        from hs_net.proxy import DIRECT, _ProxyInfo, _ProxyServer

        server = _ProxyServer()
        default_info = _ProxyInfo(scheme="http", host="default", port=8080, username=None, password=None)
        identity_info = _ProxyInfo(scheme="http", host="identity-proxy", port=8080, username=None, password=None)
        server.set_upstream(default_info)
        server.register_identity("user_a", identity_info)
        server.set_rules([("*.cn", DIRECT)])

        # 域名命中 rules → DIRECT，即使有身份
        result = server._resolve_upstream("baidu.cn", identity_hash="user_a")
        assert result is DIRECT

        # 域名未命中 rules → 走身份上游
        result = server._resolve_upstream("google.com", identity_hash="user_a")
        assert result == identity_info


class TestExtractProxyAuth:
    """_extract_proxy_auth 辅助函数测试。"""

    def test_extract_basic_auth(self):
        """正确提取 Proxy-Authorization 的 username。"""
        import base64

        from hs_net.proxy import _extract_proxy_auth

        credentials = base64.b64encode(b"my_hash:x").decode()
        header_lines = [
            b"CONNECT example.com:443 HTTP/1.1\r\n",
            f"Proxy-Authorization: Basic {credentials}\r\n".encode(),
            b"\r\n",
        ]
        assert _extract_proxy_auth(header_lines) == "my_hash"

    def test_no_proxy_auth(self):
        """无 Proxy-Authorization 时返回 None。"""
        from hs_net.proxy import _extract_proxy_auth

        header_lines = [
            b"CONNECT example.com:443 HTTP/1.1\r\n",
            b"Host: example.com:443\r\n",
            b"\r\n",
        ]
        assert _extract_proxy_auth(header_lines) is None

    def test_empty_username(self):
        """username 为空时返回 None。"""
        import base64

        from hs_net.proxy import _extract_proxy_auth

        credentials = base64.b64encode(b":password").decode()
        header_lines = [
            f"Proxy-Authorization: Basic {credentials}\r\n".encode(),
            b"\r\n",
        ]
        assert _extract_proxy_auth(header_lines) is None
