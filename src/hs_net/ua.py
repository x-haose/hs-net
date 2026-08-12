from __future__ import annotations

import random
from typing import Literal

from hs_net._ua_data import APP_POOL, BOT_POOL, DEFAULT_USER_AGENT, MOBILE_POOL, UA_POOL

__all__ = ["DEFAULT_USER_AGENT", "UserAgentShortcut", "resolve_user_agent", "user_agent_shortcuts"]

# 快捷方式别名 -> 池的键
_ALIASES = {
    "googlechrome": "chrome",
    "ff": "firefox",
    "baidu": "baiduspider",
    "google": "googlebot",
    "bing": "bingbot",
    "yandex": "yandexbot",
    "bytedance": "bytespider",
    "toutiao": "bytespider",
    "weixin": "wechat",
    "micromessenger": "wechat",
    "iphone": "ios",
}

_POOLS = {**UA_POOL, **MOBILE_POOL, **BOT_POOL, **APP_POOL}
_GROUPS = {
    "random": tuple(ua for pool in UA_POOL.values() for ua in pool),
    "mobile": tuple(ua for pool in MOBILE_POOL.values() for ua in pool),
    "bot": tuple(ua for pool in BOT_POOL.values() for ua in pool),
}

# 供 IDE 补全，实际取值以 user_agent_shortcuts() 为准
UserAgentShortcut = Literal[
    "random",
    "chrome",
    "firefox",
    "edge",
    "safari",
    "mobile",
    "android",
    "ios",
    "bot",
    "googlebot",
    "bingbot",
    "baiduspider",
    "sogou",
    "360spider",
    "bytespider",
    "yandexbot",
    "duckduckbot",
    "applebot",
    "wechat",
]


def user_agent_shortcuts() -> list[str]:
    """列出所有可用的 User-Agent 快捷方式（含别名）。"""
    return sorted({*_GROUPS, *_POOLS, *_ALIASES})


def resolve_user_agent(ua: str | None) -> str | None:
    """解析 user_agent 配置，支持快捷方式随机取一个真实 UA。

    桌面浏览器: "random"（任意桌面浏览器）、"chrome"、"firefox"、"edge"、"safari"，
    另有别名 "googlechrome"、"ff"。

    移动端浏览器: "mobile"（任意移动端）、"android"、"ios"（别名 "iphone"）。

    搜索引擎爬虫: "bot"（任意爬虫）、"googlebot"、"bingbot"、"baiduspider"、
    "sogou"、"360spider"、"bytespider"、"yandexbot"、"duckduckbot"、"applebot"，
    另有别名 "google"、"bing"、"baidu"、"yandex"、"bytedance"、"toutiao"。

    App 内置浏览器: "wechat"（微信，别名 "weixin"、"micromessenger"）。

    快捷方式不区分大小写。不在池中的字符串一律当作自定义 UA 原样返回。

    Args:
        ua: User-Agent 配置值，可以是快捷方式或完整的 UA 字符串。

    Returns:
        解析后的 User-Agent 字符串，传入 None 则返回 None。
    """
    if not ua:
        return ua
    key = _ALIASES.get(k := ua.strip().lower(), k)
    pool = _GROUPS.get(key) or _POOLS.get(key)
    return random.choice(pool) if pool else ua  # nosec B311 - 选 UA 不是加密用途
