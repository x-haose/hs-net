"""
示例 3: 选择器 — CSS、XPath、正则、JMESPath

演示 Response 对象内置的四种数据提取方式。
"""

import asyncio

from hs_net import Net, SyncNet

# ==================== HTML 解析（CSS + XPath + 正则） ====================


def html_parsing_example():
    """从真实网页提取数据。"""
    with SyncNet(verify=False, retries=0) as net:
        resp = net.get("https://example.com")

        # --- CSS 选择器 ---
        # 获取页面标题
        title = resp.css("title::text").get()
        print(f"CSS 标题: {title}")
        # => Example Domain

        # 获取所有链接
        links = resp.css("a::attr(href)").getall()
        print(f"CSS 链接: {links}")
        # => ['https://www.iana.org/domains/example']

        # 获取链接文字
        link_text = resp.css("a::text").get()
        print(f"CSS 链接文字: {link_text}")
        # => More information...

        # --- XPath ---
        # 获取段落文本
        paragraphs = resp.xpath("//p/text()").getall()
        print(f"XPath 段落: {paragraphs}")

        # 带条件的 XPath
        link = resp.xpath("//a/@href").get()
        print(f"XPath 链接: {link}")

        # --- 正则 ---
        # 从文本中提取信息
        domain = resp.re_first(r"domain in the (\w+)")
        print(f"正则提取: {domain}")

        # 提取所有匹配
        words = resp.re(r"\b[A-Z][a-z]{5,}\b")
        print(f"正则所有匹配: {words}")


# ==================== JSON 解析（JMESPath） ====================


async def json_parsing_example():
    """从 JSON API 提取数据。"""
    async with Net(verify=False, retries=0) as net:
        resp = await net.get("https://httpbin.org/get", params={"name": "Alice", "age": "25"})

        # 简单取值
        url = resp.jmespath("url")
        print(f"\n请求 URL: {url}")

        # 嵌套取值
        host = resp.jmespath("headers.Host")
        print(f"Host: {host}")

        # 获取所有查询参数
        args = resp.jmespath("args")
        print(f"查询参数: {args}")

    # 复杂 JSON 数据的 JMESPath 查询
    print("\n--- 复杂 JMESPath 查询演示 ---")
    from hs_net.models import RequestModel
    from hs_net.response import Response

    # 模拟一个 API 响应
    resp = Response(
        url="https://api.example.com/users",
        status_code=200,
        headers={},
        cookies={},
        client_cookies={},
        content=b"",
        text="",
        json_data={
            "users": [
                {"name": "Alice", "age": 25, "skills": ["Python", "Go"], "active": True},
                {"name": "Bob", "age": 17, "skills": ["JavaScript"], "active": False},
                {"name": "Charlie", "age": 30, "skills": ["Python", "Rust"], "active": True},
                {"name": "Diana", "age": 22, "skills": ["Python", "Java"], "active": True},
            ],
            "total": 4,
        },
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
    print("=== HTML 解析示例 ===")
    html_parsing_example()

    print("\n=== JSON 解析示例 ===")
    asyncio.run(json_parsing_example())
