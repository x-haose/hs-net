from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from parsel import Selector as BaseSelector
    from parsel import SelectorList as BaseSelectorList

try:
    from parsel import Selector as BaseSelector  # type: ignore[no-redef]
    from parsel import SelectorList as BaseSelectorList  # type: ignore[no-redef]

    _HAS_PARSEL = True
except ImportError:
    _HAS_PARSEL = False
    BaseSelector = object  # type: ignore[assignment,misc]
    BaseSelectorList = object  # type: ignore[assignment,misc]


class SelectorList(BaseSelectorList):  # type: ignore[misc]
    """扩展的选择器列表，支持自动拼接域名和文本去空格。

    Attributes:
        domain: 当前页面的域名，用于将相对路径转为绝对路径。
    """

    domain: str = ""

    def _proc_result(self, value: str, domain: str, is_url: bool) -> str:
        """处理单个选择结果，执行去空格和 URL 拼接。

        Args:
            value: 选择器提取的原始值。
            domain: 页面域名。
            is_url: 是否作为 URL 处理，为 True 时自动拼接域名。

        Returns:
            处理后的字符串。
        """
        if is_url and domain and value.startswith("/"):
            value = domain + value
        if isinstance(value, str):
            value = value.strip()
        return value

    def getall(self, is_url: bool = False) -> list[str]:
        """获取所有匹配结果。

        Args:
            is_url: 是否作为 URL 处理，为 True 时自动拼接域名。

        Returns:
            处理后的结果列表。
        """
        result = super().getall()
        return [self._proc_result(x, domain=self.domain, is_url=is_url) for x in result]

    def get(self, default=None, is_url: bool = False) -> str | None:
        """获取第一个匹配结果。

        Args:
            default: 无匹配时的默认值。
            is_url: 是否作为 URL 处理，为 True 时自动拼接域名。

        Returns:
            处理后的结果字符串，无匹配时返回 default。
        """
        result = super().get(default=default)
        if result is not None:
            result = self._proc_result(result, self.domain, is_url)
        return result


class Selector(BaseSelector):  # type: ignore[misc]
    """扩展的选择器，支持向查询结果注入域名信息。"""

    selectorlist_cls = SelectorList

    def __init__(self, *args, **kwargs):
        if not _HAS_PARSEL:
            raise ImportError("选择器功能需要额外安装依赖: pip install hs-net[sp]")
        super().__init__(*args, **kwargs)

    def re(self, regex: str, replace_entities: bool = True) -> list[str]:
        """对选择器内容执行正则匹配。"""
        return super().re(regex, replace_entities=replace_entities)

    def re_first(self, regex: str, default: str | None = None, replace_entities: bool = True) -> str | None:
        """对选择器内容执行正则匹配，返回第一个结果。"""
        return super().re_first(regex, default=default, replace_entities=replace_entities)

    def css(self, query: str, domain: str | None = None) -> SelectorList:
        """执行 CSS 选择器查询。

        Args:
            query: CSS 选择器表达式。
            domain: 页面域名，会注入到结果列表中用于 URL 拼接。

        Returns:
            匹配的 SelectorList。
        """
        result = super().css(query)
        result.domain = domain or ""
        return result

    def xpath(self, query: str, namespaces=None, domain: str | None = None, **kwargs) -> SelectorList:
        """执行 XPath 选择器查询。

        Args:
            query: XPath 表达式。
            namespaces: XML 命名空间映射。
            domain: 页面域名，会注入到结果列表中用于 URL 拼接。
            **kwargs: 传递给 parsel 的其他参数。

        Returns:
            匹配的 SelectorList。
        """
        result = super().xpath(query, namespaces=namespaces, **kwargs)
        result.domain = domain or ""
        return result
