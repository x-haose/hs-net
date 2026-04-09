"""
示例 11: ProxyService 代理归一化服务

统一处理 HTTP/SOCKS5/认证代理，支持代理切换和代理链。

运行前请替换 PROXY_LIST 为你自己可用的代理地址。
"""

import asyncio

from hs_net import Net, ProxyProvider, ProxyService, SyncNet

# ==================== 配置 ====================

# 替换为你自己的代理地址
PROXY_LIST = [
    "socks5://174.77.111.197:4145",
    "http://195.114.209.50:80",
]

TEST_URL = "http://ip-api.com/json/"


# ==================== 1. 固定代理 ====================


def fixed_proxy():
    """单个代理，ProxyService 自动转为本地 HTTP 代理。"""
    svc = ProxyService(PROXY_LIST[0])

    with SyncNet(proxy=svc, verify=False, retries=0, timeout=10) as net:
        resp = net.get(TEST_URL)
        print(f"  IP: {resp.json_data['query']}")
        print(f"  本地代理: {net.proxy_service.local_url}")


# ==================== 2. 代理切换 ====================


def switch_proxy():
    """多个代理，switch() 切换到下一个。"""
    svc = ProxyService(PROXY_LIST)

    with SyncNet(proxy=svc, verify=False, retries=0, timeout=10) as net:
        for i in range(len(PROXY_LIST)):
            resp = net.get(TEST_URL)
            print(f"  代理 {i + 1}: {resp.json_data['query']}")
            net.proxy_service.switch()


# ==================== 3. 隐式创建 ====================


def implicit_proxy():
    """直接传列表，自动创建 ProxyService。"""
    with SyncNet(proxy=PROXY_LIST, verify=False, retries=0, timeout=10) as net:
        resp = net.get(TEST_URL)
        print(f"  IP: {resp.json_data['query']}")


# ==================== 4. 自定义代理源 ====================


def custom_provider():
    """实现 ProxyProvider 对接任意代理源（API、Redis、文件等）。"""

    class MyProvider(ProxyProvider):
        def __init__(self):
            self._proxies = PROXY_LIST
            self._index = 0

        def get_proxy(self) -> str:
            proxy = self._proxies[self._index % len(self._proxies)]
            self._index += 1
            return proxy

    svc = ProxyService(provider=MyProvider())

    with SyncNet(proxy=svc, verify=False, retries=0, timeout=10) as net:
        resp = net.get(TEST_URL)
        print(f"  IP: {resp.json_data['query']}")


# ==================== 5. 代理链 ====================


def transit_proxy():
    """通过中转代理连接上游（如国内通过 Clash 访问海外认证代理）。

    链路: httpx → ProxyService → Clash(中转) → 海外认证代理 → 目标站

    """
    svc = ProxyService(
        "http://user:pass@overseas-proxy.com:4600",
        transit="http://127.0.0.1:7897",
    )
    with SyncNet(proxy=svc) as net:
        resp = net.get("http://ip-api.com/json/")
        print(f"  IP: {resp.json_data['query']}")


# ==================== 6. 异步用法 ====================


async def async_proxy():
    """异步客户端 + ProxyService。"""
    svc = ProxyService(PROXY_LIST[0])

    async with Net(proxy=svc, verify=False, retries=0, timeout=10) as net:
        resp = await net.get(TEST_URL)
        print(f"  IP: {resp.json_data['query']}")


# ==================== 运行 ====================

if __name__ == "__main__":
    print("=== 1. 固定代理 ===")
    fixed_proxy()

    print("\n=== 2. 代理切换 ===")
    switch_proxy()

    print("\n=== 3. 隐式创建 ===")
    implicit_proxy()

    print("\n=== 4. 自定义代理源 ===")
    custom_provider()

    print("\n=== 5. 代理链 ===")
    transit_proxy()

    print("\n=== 6. 异步 ===")
    asyncio.run(async_proxy())
