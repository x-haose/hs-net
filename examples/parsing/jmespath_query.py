"""
JMESPath JSON 查询

从 JSON 响应中提取数据，支持过滤、投影、聚合等高级查询。
"""

import asyncio
import json

from hs_net import Net
from hs_net.models import RequestModel
from hs_net.response import Response


async def basic_example():
    """从真实 API 提取 JSON 数据。"""
    async with Net(retries=0) as net:
        resp = await net.get("https://httpbin.org/get", params={"name": "Alice", "age": "25"})

        # 简单取值
        url = resp.jmespath("url")
        print(f"请求 URL: {url}")

        # 嵌套取值
        host = resp.jmespath("headers.Host")
        print(f"Host: {host}")

        # 获取所有查询参数
        args = resp.jmespath("args")
        print(f"查询参数: {args}")


def advanced_example():
    """复杂 JMESPath 查询演示（使用模拟数据）。"""
    mock_data = {
        "users": [
            {"name": "Alice", "age": 25, "skills": ["Python", "Go"], "active": True},
            {"name": "Bob", "age": 17, "skills": ["JavaScript"], "active": False},
            {"name": "Charlie", "age": 30, "skills": ["Python", "Rust"], "active": True},
            {"name": "Diana", "age": 22, "skills": ["Python", "Java"], "active": True},
        ],
        "total": 4,
    }
    resp = Response(
        url="https://api.example.com/users",
        status_code=200,
        headers={"Content-Type": "application/json"},
        cookies={},
        client_cookies={},
        content=json.dumps(mock_data).encode(),
        request_data=RequestModel(url="https://api.example.com/users"),
    )

    # 获取所有用户名
    print("所有用户:", resp.jmespath("users[*].name"))
    # => ['Alice', 'Bob', 'Charlie', 'Diana']

    # 筛选活跃用户
    print("活跃用户:", resp.jmespath("users[?active].name"))
    # => ['Alice', 'Charlie', 'Diana']

    # 筛选成年用户
    print("成年用户:", resp.jmespath("users[?age >= `18`].name"))
    # => ['Alice', 'Charlie', 'Diana']

    # 获取第一个用户的技能
    print("Alice 技能:", resp.jmespath("users[0].skills"))
    # => ['Python', 'Go']

    # 多字段选择
    print("姓名+年龄:", resp.jmespath("users[*].[name, age]"))
    # => [['Alice', 25], ['Bob', 17], ['Charlie', 30], ['Diana', 22]]

    # 获取总数
    print("总数:", resp.jmespath("total"))
    # => 4

    # 不存在的字段返回 None
    print("不存在:", resp.jmespath("nonexistent.field"))
    # => None


if __name__ == "__main__":
    print("=== 基础 JMESPath 查询 ===")
    asyncio.run(basic_example())

    print("\n=== 高级 JMESPath 查询 ===")
    advanced_example()
