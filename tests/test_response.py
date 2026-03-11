"""测试 response — Response、Selector、JMESPath。"""

from __future__ import annotations


class TestResponseBasic:
    """Response 基本属性测试。"""

    def test_attributes(self, make_response):
        resp = make_response(url="https://example.com/page", status_code=200)
        assert resp.url == "https://example.com/page"
        assert resp.status_code == 200
        assert resp.domain == "https://example.com"
        assert resp.host == "example.com"

    def test_ok_property(self, make_response):
        assert make_response(status_code=200).ok is True
        assert make_response(status_code=201).ok is True
        assert make_response(status_code=299).ok is True
        assert make_response(status_code=301).ok is False
        assert make_response(status_code=404).ok is False
        assert make_response(status_code=500).ok is False

    def test_repr(self, make_response):
        resp = make_response(url="https://example.com", status_code=200)
        assert "200" in repr(resp)
        assert "example.com" in repr(resp)

    def test_cookies(self, make_response):
        resp = make_response(cookies={"session": "abc123"})
        assert resp.cookies == {"session": "abc123"}

    def test_headers(self, make_response):
        resp = make_response(headers={"Content-Type": "text/html", "X-Custom": "value"})
        assert resp.headers["X-Custom"] == "value"

    def test_content_bytes(self, make_response):
        resp = make_response(text="hello")
        assert resp.content == b"hello"


class TestResponseCSS:
    """CSS 选择器测试。"""

    def test_css_text(self, make_response):
        resp = make_response()
        assert resp.css("h1.title::text").get() == "Hello World"

    def test_css_title(self, make_response):
        resp = make_response()
        assert resp.css("title::text").get() == "测试页面"

    def test_css_list(self, make_response):
        resp = make_response()
        fruits = resp.css("li.fruit a::text").getall()
        assert fruits == ["苹果", "香蕉", "樱桃"]

    def test_css_attr(self, make_response):
        resp = make_response()
        hrefs = resp.css("li.fruit a::attr(href)").getall()
        assert hrefs == ["/apple", "/banana", "/cherry"]

    def test_css_no_match(self, make_response):
        resp = make_response()
        assert resp.css("div.nonexistent::text").get() is None
        assert resp.css("div.nonexistent::text").get(default="fallback") == "fallback"
        assert resp.css("div.nonexistent::text").getall() == []


class TestResponseXPath:
    """XPath 选择器测试。"""

    def test_xpath_text(self, make_response):
        resp = make_response()
        assert resp.xpath("//h1[@class='title']/text()").get() == "Hello World"

    def test_xpath_list(self, make_response):
        resp = make_response()
        fruits = resp.xpath("//li[@class='fruit']/a/text()").getall()
        assert fruits == ["苹果", "香蕉", "樱桃"]

    def test_xpath_attr(self, make_response):
        resp = make_response()
        hrefs = resp.xpath("//li[@class='fruit']/a/@href").getall()
        assert hrefs == ["/apple", "/banana", "/cherry"]


class TestResponseRegex:
    """正则匹配测试。"""

    def test_re(self, make_response):
        resp = make_response()
        prices = resp.re(r"价格: (\d+)元")
        assert prices == ["99"]

    def test_re_first(self, make_response):
        resp = make_response()
        price = resp.re_first(r"价格: (\d+)元")
        assert price == "99"

    def test_re_first_default(self, make_response):
        resp = make_response()
        result = resp.re_first(r"不存在的 (\d+)", default="N/A")
        assert result == "N/A"

    def test_re_multiple_matches(self, make_response):
        html = "<p>a=1</p><p>a=2</p><p>a=3</p>"
        resp = make_response(text=html)
        matches = resp.re(r"a=(\d+)")
        assert matches == ["1", "2", "3"]


class TestResponseJMESPath:
    """JMESPath JSON 查询测试。"""

    def test_simple_value(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        assert resp.jmespath("code") == 200

    def test_nested_value(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        assert resp.jmespath("pagination.page") == 1
        assert resp.jmespath("pagination.total") == 100

    def test_index_access(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        assert resp.jmespath("data[0].name") == "Alice"
        assert resp.jmespath("data[2].name") == "Charlie"

    def test_wildcard(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        names = resp.jmespath("data[*].name")
        assert names == ["Alice", "Bob", "Charlie"]

    def test_filter(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        adults = resp.jmespath("data[?age > `18`].name")
        assert adults == ["Alice", "Charlie"]

    def test_filter_by_role(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        admins = resp.jmespath("data[?role == `admin`].name")
        assert admins == ["Alice", "Charlie"]

    def test_multi_select(self, make_response, json_data):
        resp = make_response(json_data=json_data)
        result = resp.jmespath("data[0].[name, age]")
        assert result == ["Alice", 25]

    def test_none_json_returns_none(self, make_response):
        resp = make_response(json_data=None)
        assert resp.jmespath("any.path") is None

    def test_list_json_data(self, make_response):
        resp = make_response(json_data=[{"a": 1}, {"a": 2}])
        assert resp.jmespath("[*].a") == [1, 2]


class TestResponseToUrl:
    """URL 转换测试。"""

    def test_relative_to_absolute(self, make_response):
        resp = make_response(url="https://example.com/page")
        result = resp.to_url("/other")
        assert result == ["https://example.com/other"]

    def test_multiple_urls(self, make_response):
        resp = make_response(url="https://example.com")
        result = resp.to_url(["/a", "/b", "/c"])
        assert len(result) == 3

    def test_absolute_url_filtered(self, make_response):
        resp = make_response(url="https://example.com")
        result = resp.to_url(["https://other.com/page", "/local"])
        assert result == ["https://example.com/local"]

    def test_string_input(self, make_response):
        resp = make_response(url="https://example.com")
        result = resp.to_url("/page")
        assert isinstance(result, list)
        assert len(result) == 1


class TestSelectorLazy:
    """Selector 懒加载测试。"""

    def test_selector_lazy_init(self, make_response):
        resp = make_response()
        assert resp._selector is None
        _ = resp.css("h1::text").get()
        assert resp._selector is not None

    def test_selector_reused(self, make_response):
        resp = make_response()
        _ = resp.css("h1::text")
        s1 = resp._selector
        _ = resp.xpath("//h1")
        s2 = resp._selector
        assert s1 is s2
