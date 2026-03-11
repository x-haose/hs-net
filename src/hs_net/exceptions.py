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


# 向后兼容别名
RequestStatusException = StatusException
