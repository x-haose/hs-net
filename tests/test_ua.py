"""测试 ua.py — User-Agent 解析与内置 UA 数据。"""

from __future__ import annotations

import re

import pytest

from hs_net._ua_data import APP_POOL, BOT_POOL, DEFAULT_USER_AGENT, MOBILE_POOL, UA_POOL
from hs_net.ua import resolve_user_agent, user_agent_shortcuts

# 每个浏览器池里的 UA 必须带有的标识
_BROWSER_MARKERS = {
    "chrome": r"Chrome/[\d.]+ Safari/[\d.]+$",
    "firefox": r"Firefox/[\d.]+$",
    "edge": r"Edg/[\d.]+$",
    "safari": r"Version/[\d.]+ Safari/[\d.]+$",
}
_BROWSER_CASES = [(k, k) for k in _BROWSER_MARKERS] + [("ff", "firefox"), ("googlechrome", "chrome")]
_BOT_CASES = [(k, k) for k in BOT_POOL] + [("google", "googlebot"), ("baidu", "baiduspider"), ("bing", "bingbot")]


class TestResolveUserAgent:
    def test_none_returns_none(self):
        assert resolve_user_agent(None) is None

    def test_empty_returns_empty(self):
        assert resolve_user_agent("") == ""

    def test_custom_string_passthrough(self):
        custom = "MyApp/1.0 (Custom UA)"
        assert resolve_user_agent(custom) == custom

    @pytest.mark.parametrize("value", ["Chrome", "CHROME", " chrome ", "WeChat"])
    def test_shortcut_is_case_and_space_insensitive(self, value):
        assert resolve_user_agent(value) != value

    @pytest.mark.parametrize("custom", ["MyBot/1.0", "Mozilla/5.0 (X11; Linux x86_64)", "curl/8.4.0", "myagent"])
    def test_anything_not_in_pool_is_custom_ua(self, custom):
        """不在池中的一律当自定义 UA，不猜用户是不是写错了。"""
        assert resolve_user_agent(custom) == custom

    def test_shortcuts_listing(self):
        available = user_agent_shortcuts()
        assert {"random", "bot", "chrome", "wechat", "baiduspider"} <= set(available)
        assert all(resolve_user_agent(name) for name in available)

    @pytest.mark.parametrize(("shortcut", "pool"), _BROWSER_CASES)
    def test_browser_shortcut(self, shortcut, pool):
        ua = resolve_user_agent(shortcut)
        assert ua in UA_POOL[pool]
        assert re.search(_BROWSER_MARKERS[pool], ua)

    @pytest.mark.parametrize(("shortcut", "pool"), _BOT_CASES)
    def test_bot_shortcut(self, shortcut, pool):
        assert resolve_user_agent(shortcut) in BOT_POOL[pool]

    def test_random_only_gives_browsers(self):
        """random 是"随机浏览器"，不该混进爬虫 UA。"""
        browsers = {u for p in UA_POOL.values() for u in p}
        assert all(resolve_user_agent("random") in browsers for _ in range(30))

    def test_bot_group_only_gives_bots(self):
        bots = {u for p in BOT_POOL.values() for u in p}
        assert all(resolve_user_agent("bot") in bots for _ in range(30))

    def test_random_gives_different_results(self):
        assert len({resolve_user_agent("random") for _ in range(20)}) >= 2


class TestUAPool:
    def test_pools_not_empty(self):
        assert set(UA_POOL) == set(_BROWSER_MARKERS)
        assert all(len(pool) >= 3 for pool in UA_POOL.values())

    def test_all_desktop(self):
        """移动端 UA 会让站点返回移动版页面，浏览器池里不该有。"""
        mobile = [u for p in UA_POOL.values() for u in p if re.search(r"Mobile|Android|iPhone|iPad", u)]
        assert mobile == []

    def test_no_automation_or_fork_markers(self):
        """Headless 是反爬的直接识别点；魔改浏览器的指纹与主流不一致。"""
        pattern = r"Headless|PhantomJS|Electron|OPR/|Vivaldi|Brave"
        bad = [u for p in UA_POOL.values() for u in p if re.search(pattern, u, re.I)]
        assert bad == []

    def test_versions_are_recent(self):
        """版本停在老版本说明数据该刷新了。"""
        floors = {"chrome": 145, "firefox": 145, "edge": 145, "safari": 20}
        for name, pool in UA_POOL.items():
            newest = max(int(re.search(r"(?:Chrome|Firefox|Version|Edg)/(\d+)", u).group(1)) for u in pool)
            assert newest >= floors[name], f"{name} 最高版本仅 {newest}，跑 scripts/gen_ua_data.py 刷新"

    def test_default_is_newest_windows_chrome(self):
        assert DEFAULT_USER_AGENT in UA_POOL["chrome"]
        assert "Windows NT" in DEFAULT_USER_AGENT
        versions = [int(re.search(r"Chrome/(\d+)", u).group(1)) for u in UA_POOL["chrome"] if "Windows NT" in u]
        assert int(re.search(r"Chrome/(\d+)", DEFAULT_USER_AGENT).group(1)) == max(versions)


class TestMobilePool:
    @pytest.mark.parametrize(("shortcut", "pool"), [("android", "android"), ("ios", "ios"), ("iphone", "ios")])
    def test_platform_shortcut(self, shortcut, pool):
        assert resolve_user_agent(shortcut) in MOBILE_POOL[pool]

    def test_mobile_group(self):
        everything = {u for p in MOBILE_POOL.values() for u in p}
        assert all(resolve_user_agent("mobile") in everything for _ in range(30))

    def test_not_in_random(self):
        """移动端会让站点返回移动版页面，得显式选，不能混进 random。"""
        desktop = {u for p in UA_POOL.values() for u in p}
        assert all(resolve_user_agent("random") in desktop for _ in range(30))

    def test_platforms_match_their_pool(self):
        assert all(re.search(r"Android", u) for u in MOBILE_POOL["android"])
        assert all(re.search(r"iPhone|iPad", u) for u in MOBILE_POOL["ios"])

    def test_no_embedded_webviews(self):
        """App 内嵌 WebView 不是浏览器：wv 是 Android WebView，GSA 是 Google App。"""
        bad = [u for p in MOBILE_POOL.values() for u in p if re.search(r"; wv\)|GSA/|MicroMessenger", u)]
        assert bad == []

    def test_os_versions_not_ancient(self):
        """老系统版本拿来伪装只会显眼。"""
        for ua in MOBILE_POOL["android"]:
            assert int(re.search(r"Android (\d+)", ua).group(1)) >= 10, ua
        for ua in MOBILE_POOL["ios"]:
            assert int(re.search(r"OS (\d+)[_.]", ua).group(1)) >= 15, ua


class TestBotPool:
    def test_covers_chinese_search_engines(self):
        """中文生态是选用 crawler-user-agents 数据源的主要理由。"""
        assert {"baiduspider", "sogou", "360spider", "bytespider"} <= set(BOT_POOL)

    def test_each_bot_ua_carries_its_own_name(self):
        """UA 里必须带自身标识，否则伪装无意义。"""
        tokens = {"360spider": "360spider", "sogou": "sogou"}
        for name, pool in BOT_POOL.items():
            token = tokens.get(name, name)
            assert all(token in u.lower() for u in pool), name

    def test_no_impostors(self):
        """第三方声称兼容主流 bot 的 UA 换不来放行，必须排除。"""
        pattern = r"like Googlebot|Fake-|compatible with|seoanalyzer"
        bad = [u for p in BOT_POOL.values() for u in p if re.search(pattern, u, re.I)]
        assert bad == []

    def test_well_formed(self):
        """上游收了畸形样本（缺右括号等），识别时无所谓，发请求会露馅。"""
        bad = [u for p in BOT_POOL.values() for u in p if u.count("(") != u.count(")") or "  " in u]
        assert bad == []

    def test_kept_small(self):
        """每个爬虫留标准形态即可，站点认标识不认变体。"""
        assert all(len(pool) <= 2 for pool in BOT_POOL.values())


class TestAppPool:
    @pytest.mark.parametrize("shortcut", ["wechat", "weixin", "micromessenger"])
    def test_wechat_shortcut(self, shortcut):
        assert resolve_user_agent(shortcut) in APP_POOL["wechat"]

    def test_wechat_not_in_random(self):
        """random 是"随机浏览器"，不该给出 App 内置浏览器。"""
        browsers = {u for p in UA_POOL.values() for u in p}
        assert all(resolve_user_agent("random") in browsers for _ in range(30))

    def test_wechat_covers_ios_and_android(self):
        uas = APP_POOL["wechat"]
        assert any("iPhone" in u for u in uas)
        assert any("Android" in u for u in uas)
        assert all("MicroMessenger/" in u for u in uas)

    def test_wechat_version_hex_matches_version(self):
        """UA 尾部的 hex 必须和版本号一致 —— 对不上等于自曝是伪造的。

        编码规律: [平台位|major, minor, patch, build]，iOS 平台位 0x10、Android 0x20。
        """
        for ua in APP_POOL["wechat"]:
            ver, hexs = re.search(r"MicroMessenger/([\d.]+)\((0x[0-9a-f]{8})\)", ua).groups()
            major, minor, patch = (int(p) for p in ver.split(".")[:3])
            raw = bytes.fromhex(hexs[2:])
            platform = 0x20 if "Android" in ua else 0x10
            assert raw[0] == platform | major, ua
            assert (raw[1], raw[2]) == (minor, patch), ua

    def test_wechat_ios_versions_are_diverse(self):
        """iOS 版本取自真实流量分布，不该退化成单一写死值。"""
        versions = {m.group(1) for u in APP_POOL["wechat"] if (m := re.search(r"iPhone OS (\d+_\d+)", u))}
        assert len(versions) >= 3, versions

    def test_wechat_version_is_current(self):
        """版本停在老版本说明数据该刷新了（8.0.75 于 2026-06 发布）。"""
        for ua in APP_POOL["wechat"]:
            ver = re.search(r"MicroMessenger/(\d+)\.(\d+)\.(\d+)", ua)
            major, _, patch = (int(g) for g in ver.groups())
            assert (major, patch) >= (8, 70), f"{ua}\n跑 scripts/gen_ua_data.py 刷新"
