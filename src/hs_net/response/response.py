from __future__ import annotations

import json as _json
from typing import Any
from urllib.parse import urljoin, urlparse

from hs_net.models import RequestModel
from hs_net.response.selector import Selector, SelectorList


class Response:
    """统一的 HTTP 响应对象，内置选择器解析能力。

    text 和 json_data 均为懒加载属性，仅在首次访问时解码/解析，
    避免对二进制响应（如图片、文件下载）做无意义的解码操作。

    Attributes:
        url: 最终响应的 URL（可能经过重定向）。
        status_code: HTTP 状态码。
        headers: 响应头字典。
        cookies: 本次响应返回的 cookies。
        client_cookies: 客户端会话级别的 cookies。
        content: 响应体的原始字节。
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
            request_data: 本次请求的 RequestModel。
        """
        self.url = url
        self.status_code = status_code
        self.headers = headers
        self.cookies = cookies
        self.client_cookies = client_cookies
        self.content = content
        self.request_data = request_data

        _parsed = urlparse(self.url)
        self.domain: str = f"{_parsed.scheme}://{_parsed.netloc}"
        self.host: str = _parsed.hostname or ""

        self._text: str | None = None
        self._json_data: Any = None
        self._json_loaded: bool = False
        self._selector: Selector | None = None

    def _detect_charset(self) -> str:
        """从 Content-Type 响应头中提取字符编码。

        Returns:
            字符编码名称，默认 utf-8。
        """
        ct = self.headers.get("Content-Type", "")
        for part in ct.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                return part.split("=", 1)[1].strip().strip('"')
        return "utf-8"

    @property
    def text(self) -> str:
        """响应体的文本内容（懒加载，首次访问时解码）。

        Returns:
            解码后的文本字符串。
        """
        if self._text is None:
            charset = self._detect_charset()
            try:
                self._text = self.content.decode(charset)
            except (UnicodeDecodeError, LookupError):
                self._text = self.content.decode("utf-8", errors="replace")
        return self._text

    @property
    def json_data(self) -> Any:
        """响应体解析后的 JSON 数据（懒加载，首次访问时解析）。

        Returns:
            解析后的 JSON 数据，解析失败返回 None。
        """
        if not self._json_loaded:
            self._json_loaded = True
            try:
                self._json_data = _json.loads(self.content)
            except (_json.JSONDecodeError, UnicodeDecodeError, ValueError):
                self._json_data = None
        return self._json_data

    @property
    def json_dict(self) -> dict:
        """返回 JSON dict，非 dict 时抛 TypeError。"""
        data = self.json_data
        if not isinstance(data, dict):
            raise TypeError(f"期望 dict，实际为 {type(data).__name__}")
        return data

    @property
    def json_list(self) -> list:
        """返回 JSON list，非 list 时抛 TypeError。"""
        data = self.json_data
        if not isinstance(data, list):
            raise TypeError(f"期望 list，实际为 {type(data).__name__}")
        return data

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
        try:
            import jmespath as _jmespath
        except ImportError as e:
            raise ImportError("JMESPath 功能需要额外安装依赖: pip install hs-net[sp]") from e
        if self.json_data is None:
            return None
        return _jmespath.search(expression, self.json_data)

    def to_url(self, urls: list[str] | str) -> list[str]:
        """将相对路径转为基于当前响应 URL 的绝对路径。

        Args:
            urls: 单个 URL 字符串或 URL 列表。

        Returns:
            转换后的绝对路径列表（已是 http 开头的会被过滤）。
        """
        if isinstance(urls, str):
            urls = [urls]
        return [url if url.startswith(("http://", "https://")) else urljoin(self.url, url) for url in urls]

    def __repr__(self) -> str:
        return f"<Response [{self.status_code}] {self.url}>"
