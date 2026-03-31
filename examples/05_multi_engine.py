"""
示例 5: 多引擎切换

hs-net 支持 5 种 HTTP 引擎，各有特点。本示例演示如何切换引擎以及各引擎的适用场景。

注意: httpx 为默认引擎，其他引擎需按需安装:
    pip install hs-net[aiohttp]      # aiohttp
    pip install hs-net[curl]         # curl-cffi
    pip install hs-net[requests]     # requests
    pip install hs-net[requests-go]  # requests-go
    pip install hs-net[all]          # 全部引擎
"""

import asyncio

from hs_net import EngineEnum, Net, SyncNet

TEST_URL = "https://example.com"


def sync_engines():
    """同步引擎对比（4 种可用）。"""

    # ---------- httpx（默认）----------
    # 特点：现代 HTTP 库，支持 HTTP/2
    with SyncNet(engine="httpx", verify=False, retries=0) as net:
        resp = net.get(TEST_URL)
        print(f"httpx:        {resp.status_code}")

    # ---------- requests ----------
    # 特点：最经典的 Python HTTP 库，兼容性好
    with SyncNet(engine="requests", verify=False, retries=0) as net:
        resp = net.get(TEST_URL)
        print(f"requests:     {resp.status_code}")

    # ---------- curl_cffi ----------
    # 特点：支持浏览器 TLS 指纹模拟，反爬利器
    with SyncNet(
        engine="curl_cffi",
        verify=False,
        retries=0,
        engine_options={"impersonate": "chrome120"},  # 模拟 Chrome 120 指纹
    ) as net:
        resp = net.get(TEST_URL)
        print(f"curl_cffi:    {resp.status_code}")

    # ---------- requests_go ----------
    # 特点：Go 语言实现，性能好
    with SyncNet(engine="requests_go", verify=False, retries=0) as net:
        resp = net.get(TEST_URL)
        print(f"requests_go:  {resp.status_code}")


async def async_engines():
    """异步引擎对比（4 种可用，requests 不支持异步）。"""

    # ---------- httpx（默认）----------
    async with Net(engine="httpx", verify=False, retries=0) as net:
        resp = await net.get(TEST_URL)
        print(f"httpx:        {resp.status_code}")

    # ---------- aiohttp ----------
    # 特点：Python 最成熟的异步 HTTP 库
    async with Net(engine="aiohttp", verify=False, retries=0) as net:
        resp = await net.get(TEST_URL)
        print(f"aiohttp:      {resp.status_code}")

    # ---------- curl_cffi ----------
    async with Net(engine="curl_cffi", verify=False, retries=0) as net:
        resp = await net.get(TEST_URL)
        print(f"curl_cffi:    {resp.status_code}")

    # ---------- requests_go ----------
    async with Net(engine="requests_go", verify=False, retries=0) as net:
        resp = await net.get(TEST_URL)
        print(f"requests_go:  {resp.status_code}")


def enum_usage():
    """使用 EngineEnum 枚举指定引擎。"""
    with SyncNet(engine=EngineEnum.CURL_CFFI, verify=False, retries=0) as net:
        resp = net.get(TEST_URL)
        print(f"EngineEnum:   {resp.status_code}")


def engine_options_example():
    """引擎特定配置示例。"""
    # httpx: 关闭 HTTP/2
    with SyncNet(engine="httpx", verify=False, retries=0, engine_options={"http2": False}) as net:
        resp = net.get(TEST_URL)
        print(f"httpx (HTTP/1): {resp.status_code}")

    # curl_cffi: 自定义浏览器指纹
    with SyncNet(
        engine="curl_cffi",
        verify=False,
        retries=0,
        engine_options={"impersonate": "safari15_5"},
    ) as net:
        resp = net.get(TEST_URL)
        print(f"curl_cffi (Safari): {resp.status_code}")


if __name__ == "__main__":
    print("=== 同步引擎 (4 种) ===")
    sync_engines()

    print("\n=== 异步引擎 (4 种) ===")
    asyncio.run(async_engines())

    print("\n=== 枚举方式 ===")
    enum_usage()

    print("\n=== 引擎特定配置 ===")
    engine_options_example()
