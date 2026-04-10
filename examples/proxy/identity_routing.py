"""
身份代理路由

根据请求中的身份信息（cookies、headers 等）自动为每个身份分配并绑定代理。
同一身份始终使用同一个代理（sticky），不同身份使用不同代理。

典型场景：多账号并发采集，每个账号需要独立的代理 IP。

用法:
    uv run python examples/proxy/identity_routing.py
"""

import asyncio

from hs_net import Net, ProxyService, RequestModel
from hs_net.proxy import ListProxyProvider

# ---- 代理池（替换为你自己的代理） ----
PROXIES = [
    "http://user:pass@proxy-host-a:port",
    "http://user:pass@proxy-host-b:port",
    "http://user:pass@proxy-host-c:port",
    "http://user:pass@proxy-host-d:port",
]

# 中转代理（如本地 Clash），不需要可设为 None
TRANSIT = None

# ---- 模拟多账号 ----
ACCOUNTS = [
    {"session": "account_a_session_token", "name": "账号A"},
    {"session": "account_b_session_token", "name": "账号B"},
    {"session": "account_c_session_token", "name": "账号C"},
    {"session": "account_d_session_token", "name": "账号D"},
]


def my_extractor(request: RequestModel) -> str | None:
    """从请求 cookies 中提取身份标识。"""
    if request.cookies and "session" in request.cookies:
        return request.cookies["session"]
    return None


async def fetch(net: Net, account: dict, index: int) -> str:
    """单次请求，返回格式化结果。"""
    resp = await net.get(
        "http://httpbin.org/ip",
        cookies={"session": account["session"]},
    )
    origin = resp.text.strip().split('"origin": "')[1].split('"')[0]
    return f"{account['name']} #{index}: {origin}"


async def main():
    proxy_service = ProxyService(
        provider=ListProxyProvider(PROXIES),
        identity_extractor=my_extractor,
        transit=TRANSIT,
    )

    async with Net(proxy=proxy_service, verify=False) as net:
        # ---- 串行：每个账号 5 次，观察 sticky ----
        print("=== 串行测试（每账号 5 次） ===")
        for account in ACCOUNTS:
            for i in range(1, 6):
                result = await fetch(net, account, i)
                print(result)
            print()

        # ---- 并发：4 个账号同时发请求 ----
        print("=== 并发测试（4 账号 × 3 次 = 12 请求同时发出） ===")
        tasks = [fetch(net, account, i) for account in ACCOUNTS for i in range(1, 4)]
        results = await asyncio.gather(*tasks)
        for r in results:
            print(r)


if __name__ == "__main__":
    asyncio.run(main())
