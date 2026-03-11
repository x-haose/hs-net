"""测试 ua.py — User-Agent 解析。"""

from __future__ import annotations

from hs_net.ua import resolve_user_agent


class TestResolveUserAgent:
    def test_none_returns_none(self):
        assert resolve_user_agent(None) is None

    def test_empty_returns_empty(self):
        assert resolve_user_agent("") == ""

    def test_random_returns_string(self):
        ua = resolve_user_agent("random")
        assert ua is not None
        assert len(ua) > 10

    def test_chrome_returns_chrome_ua(self):
        ua = resolve_user_agent("chrome")
        assert ua is not None
        assert len(ua) > 10

    def test_firefox_returns_ua(self):
        ua = resolve_user_agent("firefox")
        assert ua is not None
        assert len(ua) > 10

    def test_ff_shortcut(self):
        ua = resolve_user_agent("ff")
        assert ua is not None
        assert len(ua) > 10

    def test_edge_returns_ua(self):
        ua = resolve_user_agent("edge")
        assert ua is not None

    def test_safari_returns_ua(self):
        ua = resolve_user_agent("safari")
        assert ua is not None

    def test_custom_string_passthrough(self):
        custom = "MyApp/1.0 (Custom UA)"
        assert resolve_user_agent(custom) == custom

    def test_random_gives_different_results(self):
        """random 每次应该返回不同结果（概率性，多次取样）。"""
        results = {resolve_user_agent("random") for _ in range(10)}
        # 10 次至少应该出现 2 种不同结果
        assert len(results) >= 2
