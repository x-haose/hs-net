from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any

from blinker import Signal


class SignalManager:
    """信号中间件管理器，基于 blinker 实现请求生命周期钩子。

    使用本地 Signal 实例（而非全局命名信号），确保客户端关闭后
    信号对象可被垃圾回收，避免内存泄漏。

    管理三个信号:
        - request_before: 请求发送前触发，可修改请求参数或直接返回响应。
        - response_after: 响应返回后触发，可修改或替换响应。
        - request_retry: 请求重试时触发，可用于记录日志或修改重试策略。

    Attributes:
        request_before: 请求前信号。
        response_after: 响应后信号。
        request_retry: 请求重试信号。
    """

    def __init__(self, owner_id: int):
        """初始化信号管理器。

        使用本地 Signal() 实例而非 blinker.signal() 全局注册，
        避免在反复创建/销毁客户端（如 shortcuts 场景）时累积废弃信号。

        Args:
            owner_id: 所属 Net 实例的 id，用于隔离不同实例的信号。
        """
        self.request_before: Signal = Signal()
        self.response_after: Signal = Signal()
        self.request_retry: Signal = Signal()

    async def send(self, signal: Signal, *args: Any, **kwargs: Any):
        """异步发送信号并依次执行所有接收器，支持同步和异步回调。

        Args:
            signal: 要发送的信号。
            *args: 传递给接收器的位置参数。
            **kwargs: 传递给接收器的关键字参数。

        Yields:
            (receiver, result) 元组，receiver 为回调函数，result 为其返回值。
        """
        for receiver in signal.receivers_for(None):
            if iscoroutinefunction(receiver):
                result = await receiver(*args, **kwargs)
            else:
                result = receiver(*args, **kwargs)
            yield receiver, result

    def send_sync(self, signal: Signal, *args: Any, **kwargs: Any):
        """同步发送信号并依次执行所有接收器（仅支持同步回调）。

        Args:
            signal: 要发送的信号。
            *args: 传递给接收器的位置参数。
            **kwargs: 传递给接收器的关键字参数。

        Yields:
            (receiver, result) 元组，receiver 为回调函数，result 为其返回值。
        """
        for receiver in signal.receivers_for(None):
            result = receiver(*args, **kwargs)
            yield receiver, result

    def on_request_before(self, func: Callable) -> Callable:
        """装饰器：注册请求前中间件。

        回调函数接收 RequestModel 参数，可返回修改后的 RequestModel 或直接返回 Response。

        Args:
            func: 中间件回调函数。

        Returns:
            原函数（不做修改）。
        """
        self.request_before.connect(func)
        return func

    def on_response_after(self, func: Callable) -> Callable:
        """装饰器：注册响应后中间件。

        回调函数接收 Response 参数，可返回替换的 Response。

        Args:
            func: 中间件回调函数。

        Returns:
            原函数（不做修改）。
        """
        self.response_after.connect(func)
        return func

    def on_request_retry(self, func: Callable) -> Callable:
        """装饰器：注册重试中间件。

        回调函数接收触发重试的异常对象。

        Args:
            func: 中间件回调函数。

        Returns:
            原函数（不做修改）。
        """
        self.request_retry.connect(func)
        return func
