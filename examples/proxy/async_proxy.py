"""
异步代理

异步客户端搭配 ProxyService 使用。
"""

import asyncio

from hs_net import Net, ProxyService

# 替换为你自己的代理地址
PROXY = "http://127.0.0.1:8080"
TEST_URL = "http://ip-api.com/json/"


async def main():
    svc = ProxyService(PROXY)

    async with Net(proxy=svc, retries=0, timeout=30) as net:
        resp = await net.get(TEST_URL)
        print(f"IP: {resp.json_data['query']}")


if __name__ == "__main__":
    asyncio.run(main())
