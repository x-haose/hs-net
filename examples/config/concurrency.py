"""
并发控制

使用 concurrency 参数限制同时在跑的请求数量。
"""

import asyncio

from hs_net import Net


async def main():
    """最多同时 3 个请求。"""
    async with Net(retries=0, concurrency=3) as net:
        urls = [f"https://example.com/?page={i}" for i in range(10)]

        # 并发发送 10 个请求，但同时最多 3 个
        tasks = [net.get(url) for url in urls]
        results = await asyncio.gather(*tasks)

        print(f"并发控制: {len(results)} 个请求完成")
        print(f"全部成功: {all(r.ok for r in results)}")


if __name__ == "__main__":
    asyncio.run(main())
