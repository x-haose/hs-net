"""
异步代理

异步客户端搭配 ProxyService 使用。
循环验证所有异步引擎均支持代理。
"""

import asyncio

from hs_net import EngineEnum, Net, ProxyService

# 替换为你自己的代理地址
PROXY = "http://127.0.0.1:8080"
TEST_URL = "http://ip-api.com/json/"

# 所有支持异步的引擎（requests 不支持异步）
ASYNC_ENGINES = [
    EngineEnum.HTTPX,
    EngineEnum.AIOHTTP,
    EngineEnum.CURL_CFFI,
    EngineEnum.REQUESTS_GO,
]


async def main():
    svc = ProxyService(PROXY)

    for engine in ASYNC_ENGINES:
        async with Net(proxy=svc, engine=engine, retries=0, timeout=30) as net:
            resp = await net.get(TEST_URL)
            ip = resp.json_data["query"]
            print(f"{engine.value:12s} -> IP: {ip}")


if __name__ == "__main__":
    asyncio.run(main())
