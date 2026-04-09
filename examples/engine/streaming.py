"""
流式响应

流式下载大文件，无需将整个响应加载到内存。
"""

import asyncio
import tempfile

from hs_net import EngineEnum, Net, SyncNet

# ==================== 同步流式下载 ====================


def sync_stream():
    """同步流式下载文件。"""
    with SyncNet(retries=0) as net:  # noqa: SIM117
        with net.stream("GET", "https://example.com") as resp:
            print(f"状态码: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")

            total_bytes = 0
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                for chunk in resp:
                    f.write(chunk)
                    total_bytes += len(chunk)
                print(f"已下载: {total_bytes} 字节 -> {f.name}")


# ==================== 异步流式下载 ====================


async def async_stream():
    """异步流式下载文件。"""
    async with Net(retries=0) as net:
        resp = await net.stream("GET", "https://example.com")
        async with resp:
            print(f"状态码: {resp.status_code}")

            total_bytes = 0
            async for chunk in resp:
                total_bytes += len(chunk)
            print(f"已下载: {total_bytes} 字节")


# ==================== 流式响应属性 ====================


def stream_attributes():
    """流式响应的基本属性。"""
    with SyncNet(retries=0) as net, net.stream("GET", "https://example.com") as resp:
        print(f"URL: {resp.url}")
        print(f"状态码: {resp.status_code}")
        print(f"是否成功: {resp.ok}")
        print(f"响应头数量: {len(resp.headers)}")

        chunks = list(resp)
        content = b"".join(chunks)
        print(f"总大小: {len(content)} 字节")


# ==================== 多引擎流式下载 ====================


def multi_engine_stream():
    """不同引擎的流式下载。"""
    engines = [EngineEnum.HTTPX, EngineEnum.CURL_CFFI, EngineEnum.REQUESTS]

    for engine in engines:
        try:
            with SyncNet(engine=engine, retries=0) as net:  # noqa: SIM117
                with net.stream("GET", "https://example.com") as resp:
                    total = sum(len(chunk) for chunk in resp)
                    print(f"{engine.value}: {resp.status_code}, {total} 字节")
        except ImportError:
            print(f"{engine.value}: 未安装")


if __name__ == "__main__":
    print("=== 同步流式下载 ===")
    sync_stream()

    print("\n=== 异步流式下载 ===")
    asyncio.run(async_stream())

    print("\n=== 流式响应属性 ===")
    stream_attributes()

    print("\n=== 多引擎流式下载 ===")
    multi_engine_stream()
