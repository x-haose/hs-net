from fake_useragent import FakeUserAgent

_FAKE_UA_ATTRS = frozenset({"random", "chrome", "googlechrome", "edge", "firefox", "ff", "safari"})
_fake_ua = FakeUserAgent()


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
        return getattr(_fake_ua, ua)
    return ua
