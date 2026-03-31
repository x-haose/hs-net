"""
示例 7: 实战场景

模拟真实使用场景：网页抓取、API 调用、带中间件的批量请求。
"""

import asyncio
import time

from hs_net import Net, NetConfig, SyncNet

# ==================== 场景 1: 网页内容抓取 ====================


def scraping_example():
    """从网页中提取结构化数据。"""
    with SyncNet(verify=False, retries=2, user_agent="chrome") as net:
        resp = net.get("https://example.com")

        # 提取标题
        title = resp.css("title::text").get()
        print(f"标题: {title}")

        # 提取所有链接
        for link in resp.css("a"):
            href = link.css("::attr(href)").get()
            text = link.css("::text").get()
            print(f"链接: {text} -> {href}")

        # 提取段落文本
        paragraphs = resp.css("p::text").getall()
        for p in paragraphs:
            print(f"段落: {p}")


# ==================== 场景 2: REST API 客户端 ====================


async def api_client_example():
    """封装一个简单的 REST API 客户端。"""

    config = NetConfig(
        base_url="https://httpbin.org",
        timeout=15.0,
        retries=2,
        retry_delay=0.5,
        user_agent="MyAPIClient/1.0",
        verify=False,
        headers={"Accept": "application/json"},
    )

    async with Net(config=config) as api:
        # 获取资源列表
        resp = await api.get("/get", params={"type": "user", "limit": "10"})
        print(f"API GET: {resp.jmespath('args')}")

        # 创建资源
        resp = await api.post(
            "/post",
            json_data={
                "name": "新用户",
                "email": "user@example.com",
            },
        )
        print(f"API POST: {resp.jmespath('json.name')}")

        # 更新资源
        resp = await api.put(
            "/put",
            json_data={
                "name": "更新后的用户",
            },
        )
        print(f"API PUT: {resp.jmespath('json.name')}")


# ==================== 场景 3: 带监控的批量请求 ====================


async def batch_request_example():
    """批量请求 + 中间件监控。"""
    stats = {"total": 0, "success": 0, "fail": 0, "total_time": 0.0}

    async with Net(verify=False, retries=0, concurrency=5) as net:

        @net.on_request_before
        async def track_start(req_data):
            stats["total"] += 1

        @net.on_response_after
        async def track_result(resp):
            if resp.ok:
                stats["success"] += 1
            else:
                stats["fail"] += 1

        # 批量请求
        urls = [f"https://example.com/?id={i}" for i in range(20)]

        start = time.time()
        tasks = [net.get(url) for url in urls]
        results = await asyncio.gather(*tasks)
        stats["total_time"] = time.time() - start

        # 输出统计
        print("批量请求完成:")
        print(f"  总计: {stats['total']}")
        print(f"  成功: {stats['success']}")
        print(f"  失败: {stats['fail']}")
        print(f"  耗时: {stats['total_time']:.2f}s")
        print(f"  QPS:  {stats['total'] / stats['total_time']:.1f}")

        # 提取每个页面的标题
        titles = [r.css("title::text").get() for r in results]
        unique_titles = set(titles)
        print(f"  页面标题: {unique_titles}")


# ==================== 场景 4: 反爬场景 (curl_cffi) ====================


def anti_bot_example():
    """使用 curl_cffi 引擎模拟浏览器指纹。

    注意: 需要安装 curl-cffi 引擎: pip install hs-net[curl]
    """
    with SyncNet(
        engine="curl_cffi",
        verify=False,
        retries=0,
        user_agent="chrome",
        engine_options={"impersonate": "chrome120"},
    ) as net:
        resp = net.get("https://example.com")
        print(f"curl_cffi 反爬: {resp.status_code}")
        print(f"标题: {resp.css('title::text').get()}")


if __name__ == "__main__":
    print("=== 场景 1: 网页抓取 ===")
    scraping_example()

    print("\n=== 场景 2: REST API 客户端 ===")
    asyncio.run(api_client_example())

    print("\n=== 场景 3: 带监控的批量请求 ===")
    asyncio.run(batch_request_example())

    print("\n=== 场景 4: 反爬场景 ===")
    anti_bot_example()
