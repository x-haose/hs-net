import sys
import traceback as _tb_module

# 内部模块路径关键字，这些帧对用户没有调试价值
_INTERNAL_PATHS = ("/hs_net/", "/asyncio/", "/tenacity/")

_original_excepthook = sys.excepthook


def _hs_net_excepthook(exc_type, exc_value, exc_tb):
    """自定义异常钩子：对 hs-net 异常只展示用户代码帧，过滤内部堆栈。"""
    if isinstance(exc_value, RequestException):
        entries = _tb_module.extract_tb(exc_tb)
        filtered = [e for e in entries if not any(p in e.filename for p in _INTERNAL_PATHS)]
        sys.stderr.write("Traceback (most recent call last):\n")
        for line in _tb_module.format_list(filtered):
            sys.stderr.write(line)
        for line in _tb_module.format_exception_only(exc_type, exc_value):
            sys.stderr.write(line)
    else:
        _original_excepthook(exc_type, exc_value, exc_tb)


sys.excepthook = _hs_net_excepthook


class RequestException(Exception):
    """请求异常基类，所有 hs-net 异常的父类。

    Attributes:
        exception_type: 原始异常的类型名称。
        exception_msg: 原始异常的消息内容。
    """

    def __init__(self, exception_type: str = "", exception_msg: str | list = ""):
        """初始化请求异常。

        Args:
            exception_type: 原始异常的类型名称。
            exception_msg: 原始异常的消息内容。
        """
        self.exception_type = exception_type
        self.exception_msg = exception_msg
        super().__init__(f"[{exception_type}]: {exception_msg}")


class StatusException(RequestException):
    """HTTP 状态码异常，当响应状态码不在 2xx 范围内时抛出。

    Attributes:
        code: HTTP 状态码。
        url: 请求的 URL 地址。
    """

    def __init__(self, code: int, url: str = ""):
        """初始化状态码异常。

        Args:
            code: HTTP 状态码。
            url: 请求的 URL 地址。
        """
        self.code = code
        self.url = url
        super().__init__("StatusException", f"HTTP {code}: {url}")


class TimeoutException(RequestException):
    """请求超时异常。

    Attributes:
        url: 请求的 URL 地址。
        timeout: 超时时间（秒）。
    """

    def __init__(self, url: str = "", timeout: float | None = None):
        """初始化超时异常。

        Args:
            url: 请求的 URL 地址。
            timeout: 超时时间（秒）。
        """
        self.url = url
        self.timeout = timeout
        super().__init__("TimeoutException", f"timeout={timeout}s url={url}")


class ConnectionException(RequestException):
    """连接异常，包括 DNS 解析失败、连接拒绝、SSL 错误等。

    Attributes:
        url: 请求的 URL 地址。
    """

    def __init__(self, url: str = "", message: str = ""):
        """初始化连接异常。

        Args:
            url: 请求的 URL 地址。
            message: 错误描述。
        """
        self.url = url
        super().__init__("ConnectionException", f"{message} url={url}")


class RetryExhausted(RequestException):
    """重试耗尽异常，所有重试均失败后抛出。

    Attributes:
        attempts: 已尝试的次数。
        last_exception: 最后一次异常。
    """

    def __init__(self, attempts: int, last_exception: Exception, url: str = ""):
        """初始化重试耗尽异常。

        Args:
            attempts: 已尝试的次数。
            last_exception: 最后一次异常。
            url: 请求的 URL 地址。
        """
        self.attempts = attempts
        self.last_exception = last_exception
        self.url = url
        exc_type = type(last_exception).__name__
        super().__init__("RetryExhausted", f"{attempts} 次重试全部失败 [{exc_type}]: {last_exception} url={url}")


class EngineNotInstalled(RequestException):
    """引擎依赖未安装异常。

    当用户指定的引擎对应的第三方库未安装时抛出，
    异常消息中包含安装命令以引导用户安装。

    Attributes:
        engine_name: 引擎名称。
        install_package: 安装包名称（含 extras）。
    """

    def __init__(self, engine_name: str, install_package: str):
        """初始化引擎未安装异常。

        Args:
            engine_name: 引擎名称，如 "aiohttp"、"curl-cffi"。
            install_package: 安装包名称，如 "hs-net[aiohttp]"。
        """
        self.engine_name = engine_name
        self.install_package = install_package
        super().__init__(
            "EngineNotInstalled",
            f"引擎 {engine_name} 需要额外安装依赖: pip install {install_package}",
        )
