from __future__ import annotations

from typing import Any

import jmespath
from furl import furl

from hs_net.models import RequestModel
from hs_net.response.selector import Selector, SelectorList


class Response:
    """统一的 HTTP 响应对象，内置选择器解析能力。

    Attributes:
        url: 最终响应的 URL（可能经过重定向）。
        status_code: HTTP 状态码。
        headers: 响应头字典。
        cookies: 本次响应返回的 cookies。
        client_cookies: 客户端会话级别的 cookies。
        content: 响应体的原始字节。
        text: 响应体的文本内容。
        json_data: 响应体解析后的 JSON 数据，解析失败为 None。
        request_data: 本次请求的 RequestModel。
        domain: 响应 URL 的域名（含协议）。
        host: 响应 URL 的主机名。
    """

    def __init__(
        self,
        url: str,
        status_code: int,
        headers: dict[str, Any],
        cookies: dict[str, str],
        client_cookies: dict[str, str],
        content: bytes,
        text: str,
        json_data: dict | list | None,
        request_data: RequestModel,
    ):
        """初始化响应对象。

        Args:
            url: 最终响应的 URL。
            status_code: HTTP 状态码。
            headers: 响应头字典。
            cookies: 本次响应返回的 cookies。
            client_cookies: 客户端会话级别的 cookies。
            content: 响应体的原始字节。
            text: 响应体的文本内容。
            json_data: 响应体解析后的 JSON 数据。
            request_data: 本次请求的 RequestModel。
        """
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.cookies = cookies
        self.client_cookies = client_cookies
        self.content = content
        self.text = text
        self.json_data = json_data
        self.request_data = request_data

        self.domain: str = furl(self.url).origin
        self.host: str = furl(self.url).host

        self._selector: Selector | None = None

    @property
    def selector(self) -> Selector:
        """懒加载选择器，只有在使用 xpath/css 时才初始化。

        Returns:
            基于响应文本的 Selector 实例。
        """
        if self._selector is None:
            self._selector = Selector(self.text)
        return self._selector

    @property
    def ok(self) -> bool:
        """状态码是否在 2xx 范围内。

        Returns:
            True 表示请求成功。
        """
        return 200 <= self.status_code < 300

    def xpath(self, query: str) -> SelectorList:
        """执行 XPath 查询。

        Args:
            query: XPath 表达式。

        Returns:
            匹配的 SelectorList。
        """
        return self.selector.xpath(query, domain=self.domain)

    def css(self, query: str) -> SelectorList:
        """执行 CSS 选择器查询。

        Args:
            query: CSS 选择器表达式。

        Returns:
            匹配的 SelectorList。
        """
        return self.selector.css(query, domain=self.domain)

    def re(self, regex: str, replace_entities: bool = True) -> list[str]:
        """对响应文本执行正则匹配。

        Args:
            regex: 正则表达式。
            replace_entities: 是否替换 HTML 字符实体（&amp; 和 &lt; 除外）。

        Returns:
            所有匹配结果的列表。
        """
        return self.selector.re(regex, replace_entities=replace_entities)

    def re_first(self, regex: str, default=None, replace_entities: bool = True) -> str | None:
        """对响应文本执行正则匹配，返回第一个结果。

        Args:
            regex: 正则表达式。
            default: 无匹配时的默认值。
            replace_entities: 是否替换 HTML 字符实体（&amp; 和 &lt; 除外）。

        Returns:
            第一个匹配结果，无匹配时返回 default。
        """
        return self.selector.re_first(regex, default=default, replace_entities=replace_entities)

    def jmespath(self, expression: str) -> Any:
        """对 JSON 响应执行 JMESPath 查询。

        Args:
            expression: JMESPath 表达式，如 "data[0].name"、"data[*].id"、"data[?age > `18`].name"。

        Returns:
            查询结果，类型取决于表达式（可能是 str、list、dict 等）。
            json_data 为 None 时返回 None。
        """
        if self.json_data is None:
            return None
        return jmespath.search(expression, self.json_data)

    def to_url(self, urls: list[str] | str) -> list[str]:
        """将相对路径转为基于当前响应 URL 的绝对路径。

        Args:
            urls: 单个 URL 字符串或 URL 列表。

        Returns:
            转换后的绝对路径列表（已是 http 开头的会被过滤）。
        """
        if isinstance(urls, str):
            urls = [urls]
        return [furl(self.url).join(url).url for url in urls if not url.startswith("http")]

    def __repr__(self) -> str:
        return f"<Response [{self.status_code}] {self.url}>"
