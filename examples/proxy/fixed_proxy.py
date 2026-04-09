"""
固定代理

使用单个代理发送请求，ProxyService 自动转为本地 HTTP 代理。

支持的代理格式:
    http://host:port
    https://host:port
    socks4://host:port
    socks5://host:port
    http://user:pass@host:port (HTTP 认证代理)
    socks5://user:pass@host:port (SOCKS5 认证代理)
"""

from hs_net import ProxyService, SyncNet

# 替换为你自己的代理地址
PROXY = "socks5://127.0.0.1:1080"
TEST_URL = "http://ip-api.com/json/"


def main():
    svc = ProxyService(PROXY)

    with SyncNet(proxy=svc, retries=0, timeout=30) as net:
        resp = net.get(TEST_URL)
        print(f"IP: {resp.json_data['query']}")
        print(f"本地代理: {net.proxy_service.local_url}")


if __name__ == "__main__":
    main()
