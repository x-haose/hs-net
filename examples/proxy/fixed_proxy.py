"""
固定代理

使用单个代理发送请求，ProxyService 自动转为本地 HTTP 代理。
循环验证所有同步引擎均支持代理。

支持的代理格式:
    http://host:port
    https://host:port
    socks4://host:port
    socks5://host:port
    http://user:pass@host:port (HTTP 认证代理)
    socks5://user:pass@host:port (SOCKS5 认证代理)
"""

from hs_net import EngineEnum, ProxyService, SyncNet

# 替换为你自己的代理地址
PROXY = "socks5://127.0.0.1:1080"
TEST_URL = "http://ip-api.com/json/"

# 所有支持同步的引擎
SYNC_ENGINES = [
    EngineEnum.HTTPX,
    EngineEnum.REQUESTS,
    EngineEnum.CURL_CFFI,
    EngineEnum.REQUESTS_GO,
]


def main():
    svc = ProxyService(PROXY)

    for engine in SYNC_ENGINES:
        with SyncNet(proxy=svc, engine=engine, retries=0, timeout=30) as net:
            resp = net.get(TEST_URL)
            ip = resp.json_data["query"]
            print(f"{engine.value:12s} -> IP: {ip}")


if __name__ == "__main__":
    main()
