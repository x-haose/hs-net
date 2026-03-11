"""测试公共 fixtures。"""

from __future__ import annotations

import pytest

from hs_net.models import RequestModel
from hs_net.response import Response


@pytest.fixture
def html_text():
    """一段用于测试选择器的 HTML 文本。"""
    return """
    <html>
    <head><title>测试页面</title></head>
    <body>
        <h1 class="title">Hello World</h1>
        <ul id="fruits">
            <li class="fruit"><a href="/apple">苹果</a></li>
            <li class="fruit"><a href="/banana">香蕉</a></li>
            <li class="fruit"><a href="/cherry">樱桃</a></li>
        </ul>
        <p class="price">价格: 99元</p>
        <p class="desc">这是一段描述文本</p>
    </body>
    </html>
    """


@pytest.fixture
def json_data():
    """一段用于测试 JMESPath 的 JSON 数据。"""
    return {
        "code": 200,
        "data": [
            {"id": 1, "name": "Alice", "age": 25, "role": "admin"},
            {"id": 2, "name": "Bob", "age": 17, "role": "user"},
            {"id": 3, "name": "Charlie", "age": 30, "role": "admin"},
        ],
        "pagination": {"page": 1, "total": 100},
    }


@pytest.fixture
def make_response(html_text):
    """构造测试用 Response 对象的工厂。"""

    def _make(
        url="https://example.com/test",
        status_code=200,
        text=None,
        json_data=None,
        headers=None,
        cookies=None,
    ):
        return Response(
            url=url,
            status_code=status_code,
            headers=headers or {"Content-Type": "text/html"},
            cookies=cookies or {},
            client_cookies={},
            content=(text or html_text).encode(),
            text=text or html_text,
            json_data=json_data,
            request_data=RequestModel(url=url),
        )

    return _make
