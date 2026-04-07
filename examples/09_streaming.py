"""
示例 9: 流式响应

演示流式下载大文件、流式读取响应体等场景。
无需将整个响应加载到内存，适合大文件下载和实时数据处理。
"""

import asyncio
import tempfile

from hs_net import Net, SyncNet

# ==================== 同步流式下载 ====================


def sync_stream_example():
    """同步流式下载文件。"""
    with SyncNet(verify=False, retries=0) as net:  # noqa: SIM117
        # 使用 with 确保流式响应被正确关闭
        with net.stream("GET", "https://example.com") as resp:
            print(f"状态码: {resp.status_code}")
            print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")

            # 分块读取并写入临时文件
            total_bytes = 0
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
                for chunk in resp:
                    f.write(chunk)
                    total_bytes += len(chunk)
                print(f"已下载: {total_bytes} 字节 -> {f.name}")


# ==================== 异步流式下载 ====================


async def async_stream_example():
    """异步流式下载文件。"""
    async with Net(verify=False, retries=0) as net:
        resp = await net.stream("GET", "https://example.com")
        async with resp:
            print(f"状态码: {resp.status_code}")

            total_bytes = 0
            async for chunk in resp:
                total_bytes += len(chunk)
            print(f"已下载: {total_bytes} 字节")


# ==================== 流式响应属性 ====================


def stream_attributes_example():
    """流式响应的基本属性。"""
    with SyncNet(verify=False, retries=0) as net, net.stream("GET", "https://example.com") as resp:
        print(f"URL: {resp.url}")
        print(f"状态码: {resp.status_code}")
        print(f"是否成功: {resp.ok}")
        print(f"响应头数量: {len(resp.headers)}")

        # 读取全部内容
        chunks = list(resp)
        content = b"".join(chunks)
        print(f"总大小: {len(content)} 字节")


# ==================== 多引擎流式下载 ====================


def multi_engine_stream():
    """不同引擎的流式下载。"""
    engines = ["httpx", "curl_cffi", "requests"]

    for engine_name in engines:
        try:
            with SyncNet(engine=engine_name, verify=False, retries=0) as net:  # noqa: SIM117
                with net.stream("GET", "https://example.com") as resp:
                    total = sum(len(chunk) for chunk in resp)
                    print(f"{engine_name}: {resp.status_code}, {total} 字节")
        except ImportError:
            print(f"{engine_name}: 未安装")


if __name__ == "__main__":
    print("=== 同步流式下载 ===")
    sync_stream_example()

    print("\n=== 异步流式下载 ===")
    asyncio.run(async_stream_example())

    print("\n=== 流式响应属性 ===")
    stream_attributes_example()

    print("\n=== 多引擎流式下载 ===")
    multi_engine_stream()
