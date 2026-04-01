from __future__ import annotations

_FAKE_UA_ATTRS = frozenset({"random", "chrome", "googlechrome", "edge", "firefox", "ff", "safari"})

# 延迟初始化，避免 import hs_net 时立即加载 UA 数据库
_fake_ua = None


def _get_fake_ua():
    """获取 FakeUserAgent 单例（首次调用时初始化）。"""
    global _fake_ua  # noqa: PLW0603
    if _fake_ua is None:
        from fake_useragent import FakeUserAgent

        _fake_ua = FakeUserAgent()
    return _fake_ua


def resolve_user_agent(ua: str | None) -> str | None:
    """解析 user_agent 配置，支持快捷方式自动生成 UA 字符串。

    支持的快捷方式: "random", "chrome", "googlechrome", "edge", "firefox", "ff", "safari"。
    传入其他字符串则原样返回。

    Args:
        ua: User-Agent 配置值，可以是快捷方式或完整的 UA 字符串。

    Returns:
        解析后的 User-Agent 字符串，传入 None 则返回 None。
    """
    if ua and ua in _FAKE_UA_ATTRS:
        return getattr(_get_fake_ua(), ua)
    return ua
