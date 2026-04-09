"""
自定义代理源

实现 ProxyProvider 对接任意代理源（API、Redis、文件等）。
"""

from hs_net import ProxyProvider, ProxyService, SyncNet

# 替换为你自己的代理地址
PROXY_LIST = [
    "http://proxy1:8080",
    "socks5://user:pass@proxy2:1080",
]
TEST_URL = "http://ip-api.com/json/"


class MyProvider(ProxyProvider):
    """自定义代理提供器，轮询返回代理地址。"""

    def __init__(self):
        self._proxies = PROXY_LIST
        self._index = 0

    def get_proxy(self) -> str:
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy


def main():
    svc = ProxyService(provider=MyProvider())

    with SyncNet(proxy=svc, retries=0, timeout=30) as net:
        resp = net.get(TEST_URL)
        print(f"IP: {resp.json_data['query']}")


if __name__ == "__main__":
    main()
