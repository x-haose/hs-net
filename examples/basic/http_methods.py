"""
各种 HTTP 方法

演示 GET、POST（JSON / 表单 / 文件上传）、PUT、PATCH、DELETE 等请求方式。
"""

import asyncio

from hs_net import Net


async def main():
    async with Net(
        base_url="https://httpbin.org",
        retries=0,
        user_agent="MyApp/1.0",
    ) as net:
        # ---------- GET 带查询参数 ----------
        resp = await net.get("/get", params={"q": "python", "page": "1"})
        print("GET 查询参数:", resp.jmespath("args"))
        # => {'q': 'python', 'page': '1'}

        # ---------- POST JSON ----------
        resp = await net.post("/post", json_data={"username": "alice", "age": 25})
        print("POST JSON:", resp.jmespath("json"))
        # => {'username': 'alice', 'age': 25}

        # ---------- POST 表单 ----------
        resp = await net.post("/post", form_data={"email": "test@example.com", "password": "123456"})
        print("POST 表单:", resp.jmespath("form"))
        # => {'email': 'test@example.com', 'password': '123456'}

        # ---------- POST 文件上传 ----------
        resp = await net.post(
            "/post",
            files={"file": ("hello.txt", b"Hello, World!", "text/plain")},
        )
        print("POST 文件:", resp.jmespath("files"))
        # => {'file': 'Hello, World!'}

        # ---------- PUT ----------
        resp = await net.put("/put", json_data={"id": 1, "name": "updated"})
        print("PUT:", resp.jmespath("json"))

        # ---------- PATCH ----------
        resp = await net.patch("/patch", json_data={"name": "patched"})
        print("PATCH:", resp.jmespath("json"))

        # ---------- DELETE ----------
        resp = await net.delete("/delete")
        print("DELETE 状态码:", resp.status_code)


if __name__ == "__main__":
    asyncio.run(main())
