"""
示例 4: 信号中间件

演示 request_before、response_after、request_retry 三种中间件的使用。
可用于日志记录、请求修改、响应缓存、统计监控等场景。
"""

import asyncio
import time

from hs_net import Net, SyncNet

# ==================== 同步中间件示例 ====================


def sync_middleware_example():
    """同步中间件：请求计时 + 日志。"""
    with SyncNet(verify=False, retries=0) as net:
        timings = {}

        @net.on_request_before
        def log_request(req_data):
            """请求发送前：记录开始时间。"""
            timings["start"] = time.time()
            print(f"  → 发送请求: {req_data.method} {req_data.url}")

        @net.on_response_after
        def log_response(resp):
            """响应返回后：计算耗时。"""
            elapsed = time.time() - timings["start"]
            print(f"  ← 收到响应: {resp.status_code} ({elapsed:.3f}s)")

        net.get("https://example.com")


# ==================== 异步中间件示例 ====================


async def async_middleware_example():
    """异步中间件：请求统计 + 自定义 Header。"""
    async with Net(verify=False, retries=0) as net:
        stats = {"total": 0, "success": 0, "fail": 0}

        @net.on_request_before
        async def add_custom_header(req_data):
            """请求发送前：自动添加自定义 Header。"""
            req_data.headers["X-Request-ID"] = f"req-{stats['total'] + 1}"
            stats["total"] += 1
            print(f"  → 请求 #{stats['total']}: {req_data.url}")

        @net.on_response_after
        async def count_results(resp):
            """响应返回后：统计成功/失败。"""
            if resp.ok:
                stats["success"] += 1
            else:
                stats["fail"] += 1

        await net.get("https://example.com")
        await net.get("https://example.com")

        print(f"  统计: 总计={stats['total']}, 成功={stats['success']}, 失败={stats['fail']}")


# ==================== 重试中间件示例 ====================


def retry_middleware_example():
    """重试中间件：记录每次重试。"""
    with SyncNet(verify=False, retries=3, raise_status=True) as net:

        @net.on_request_retry
        def on_retry(exc):
            """重试时：记录异常信息。"""
            print(f"  ⟳ 重试中，原因: {type(exc).__name__}: {exc}")

        try:
            # 访问一个会返回 404 的 URL，触发重试
            net.get("https://example.com/nonexistent-12345")
        except Exception as e:
            print(f"  ✗ 最终失败: {type(e).__name__}")


# ==================== 响应缓存中间件示例 ====================


def cache_middleware_example():
    """响应缓存：相同 URL 直接返回缓存结果。"""
    with SyncNet(verify=False, retries=0) as net:
        cache = {}

        @net.on_request_before
        def check_cache(req_data):
            """请求前检查缓存，命中则直接返回 Response。"""
            if req_data.url in cache:
                print(f"  缓存命中: {req_data.url}")
                return cache[req_data.url]
            print(f"  缓存未命中: {req_data.url}")

        @net.on_response_after
        def save_cache(resp):
            """响应后存入缓存。"""
            cache[resp.url] = resp

        # 第一次请求 —— 走网络
        resp1 = net.get("https://example.com")
        print(f"  第一次: {resp1.status_code}")

        # 第二次请求 —— 走缓存
        resp2 = net.get("https://example.com")
        print(f"  第二次: {resp2.status_code}")

        # 验证是同一个对象
        print(f"  是否同一对象: {resp1 is resp2}")


if __name__ == "__main__":
    print("=== 同步中间件：请求计时 ===")
    sync_middleware_example()

    print("\n=== 异步中间件：请求统计 ===")
    asyncio.run(async_middleware_example())

    print("\n=== 重试中间件 ===")
    retry_middleware_example()

    print("\n=== 响应缓存中间件 ===")
    cache_middleware_example()
