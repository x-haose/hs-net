"""集成测试 — Net 和 SyncNet 真实网络请求。

需要网络连接才能运行。使用 verify=False 避免本地 SSL 证书问题。
运行: uv run pytest tests/test_client_integration.py -v
"""

from __future__ import annotations

import pytest

from hs_net import Net, SyncNet
from hs_net.exceptions import RetryExhausted

# 测试 URL
TEST_URL = "https://example.com"


# ==================== SyncNet 测试 ====================


class TestSyncNetBasic:
    """SyncNet 基本功能测试。"""

    def test_get(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            assert resp.status_code == 200
            assert resp.ok is True
            assert "Example Domain" in resp.text

    def test_head(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.head(TEST_URL)
            assert resp.status_code == 200

    def test_css_selector(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            title = resp.css("title::text").get()
            assert title == "Example Domain"

    def test_xpath_selector(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            title = resp.xpath("//title/text()").get()
            assert title == "Example Domain"

    def test_regex(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            result = resp.re_first(r"<title>(.*?)</title>")
            assert result == "Example Domain"

    def test_response_attributes(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            assert resp.domain == "https://example.com"
            assert resp.host == "example.com"
            assert isinstance(resp.content, bytes)
            assert isinstance(resp.text, str)
            assert isinstance(resp.headers, dict)

    def test_cookies_property(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            _ = net.get(TEST_URL)
            cookies = net.cookies
            assert isinstance(cookies, dict)


class TestSyncNetBaseUrl:
    """SyncNet base_url 功能测试。"""

    def test_base_url(self):
        with SyncNet(engine="httpx", base_url=TEST_URL, verify=False, retries=0) as net:
            resp = net.get("/")
            assert resp.status_code == 200
            assert "Example Domain" in resp.text


class TestSyncNetConfig:
    """SyncNet 配置参数测试。"""

    def test_custom_headers(self):
        with SyncNet(engine="httpx", verify=False, retries=0, headers={"X-Test": "hello"}) as net:
            resp = net.get(TEST_URL)
            assert resp.status_code == 200

    def test_custom_user_agent(self):
        with SyncNet(engine="httpx", verify=False, retries=0, user_agent="TestBot/1.0") as net:
            resp = net.get(TEST_URL)
            assert resp.status_code == 200

    def test_raise_status_false(self):
        with SyncNet(engine="httpx", verify=False, retries=0, raise_status=False) as net:
            resp = net.get(TEST_URL + "/nonexistent-page-12345")
            assert resp.status_code == 404


class TestSyncNetSignals:
    """SyncNet 信号中间件测试。"""

    def test_request_before_signal(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            called = []

            @net.on_request_before
            def before(req_data):
                called.append(req_data.url)

            net.get(TEST_URL)
            assert len(called) == 1
            assert TEST_URL in called[0]

    def test_response_after_signal(self):
        with SyncNet(engine="httpx", verify=False, retries=0) as net:
            statuses = []

            @net.on_response_after
            def after(resp):
                statuses.append(resp.status_code)

            net.get(TEST_URL)
            assert statuses == [200]


class TestSyncNetRetry:
    """SyncNet 重试测试。"""

    def test_retry_exhausted(self):
        with (
            SyncNet(engine="httpx", verify=False, retries=2, raise_status=True) as net,
            pytest.raises(RetryExhausted),
        ):
            net.get(TEST_URL + "/nonexistent-page-12345")


class TestSyncNetMultiEngine:
    """SyncNet 多引擎测试。"""

    @pytest.mark.parametrize("engine", ["httpx", "curl_cffi", "requests"])
    def test_sync_engines(self, engine):
        with SyncNet(engine=engine, verify=False, retries=0) as net:
            resp = net.get(TEST_URL)
            assert resp.status_code == 200
            assert "Example Domain" in resp.text


# ==================== Net 异步测试 ====================


class TestNetBasic:
    """Net 异步基本功能测试。"""

    @pytest.mark.asyncio
    async def test_get(self):
        async with Net(engine="httpx", verify=False, retries=0) as net:
            resp = await net.get(TEST_URL)
            assert resp.status_code == 200
            assert "Example Domain" in resp.text

    @pytest.mark.asyncio
    async def test_head(self):
        async with Net(engine="httpx", verify=False, retries=0) as net:
            resp = await net.head(TEST_URL)
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_css_selector(self):
        async with Net(engine="httpx", verify=False, retries=0) as net:
            resp = await net.get(TEST_URL)
            title = resp.css("title::text").get()
            assert title == "Example Domain"

    @pytest.mark.asyncio
    async def test_base_url(self):
        async with Net(engine="httpx", base_url=TEST_URL, verify=False, retries=0) as net:
            resp = await net.get("/")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_raise_status_false(self):
        async with Net(engine="httpx", verify=False, retries=0, raise_status=False) as net:
            resp = await net.get(TEST_URL + "/nonexistent-page-12345")
            assert resp.status_code == 404


class TestNetSignals:
    """Net 异步信号中间件测试。"""

    @pytest.mark.asyncio
    async def test_request_before_signal(self):
        async with Net(engine="httpx", verify=False, retries=0) as net:
            called = []

            @net.on_request_before
            async def before(req_data):
                called.append(req_data.url)

            await net.get(TEST_URL)
            assert len(called) == 1

    @pytest.mark.asyncio
    async def test_response_after_signal(self):
        async with Net(engine="httpx", verify=False, retries=0) as net:
            statuses = []

            @net.on_response_after
            async def after(resp):
                statuses.append(resp.status_code)

            await net.get(TEST_URL)
            assert statuses == [200]


class TestNetMultiEngine:
    """Net 异步多引擎测试。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("engine", ["httpx", "aiohttp", "curl_cffi"])
    async def test_async_engines(self, engine):
        async with Net(engine=engine, verify=False, retries=0) as net:
            resp = await net.get(TEST_URL)
            assert resp.status_code == 200
            assert "Example Domain" in resp.text
