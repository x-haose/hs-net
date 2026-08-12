"""
反爬场景

演示两种伪装手段: curl_cffi 的 TLS 指纹模拟，以及内置 User-Agent 池。

注意: curl_cffi 引擎需要额外安装: pip install hs-net[curl]
"""

from hs_net import EngineEnum, SyncNet
from hs_net.ua import resolve_user_agent


def tls_fingerprint():
    """TLS 指纹模拟。

    不要同时指定 user_agent —— impersonate 自带的 UA 与它的 TLS 指纹、
    sec-ch-ua 等 client hints 同代，塞入外部 UA 反而会制造矛盾。
    impersonate 传 "chrome" 会自动跟随 curl-cffi 支持的最新版本。
    """
    with SyncNet(
        engine=EngineEnum.CURL_CFFI,
        retries=0,
        engine_options={"impersonate": "chrome"},
    ) as net:
        resp = net.get("https://example.com")
        print(f"TLS 指纹模拟: {resp.status_code} {resp.css('title::text').get()}")


def user_agent_pool():
    """内置 User-Agent 池，无需额外依赖。

    random / mobile 分别是桌面、移动端的随机入口；爬虫和微信需显式指定。
    """
    for label, shortcut in [
        ("随机桌面浏览器", "random"),
        ("随机移动端", "mobile"),
        ("百度蜘蛛", "baiduspider"),
        ("微信内置浏览器", "wechat"),
    ]:
        print(f"{label:8} {shortcut:12} -> {resolve_user_agent(shortcut)}")

    with SyncNet(retries=0, user_agent="wechat") as net:
        resp = net.get("https://example.com")
        print(f"\n以微信 UA 请求: {resp.status_code} {resp.css('title::text').get()}")


def main():
    tls_fingerprint()
    user_agent_pool()


if __name__ == "__main__":
    main()
