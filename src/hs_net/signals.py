from __future__ import annotations

from collections.abc import Callable
from inspect import iscoroutinefunction
from typing import Any


class SignalManager:
    """信号中间件管理器，基于简单回调列表实现请求生命周期钩子。

    管理三个信号:
        - request_before: 请求发送前触发，可修改请求参数或直接返回响应。
        - response_after: 响应返回后触发，可修改或替换响应。
        - request_retry: 请求重试时触发，可用于记录日志或修改重试策略。
    """

    def __init__(self):
        """初始化信号管理器。"""
        self.request_before: list[Callable] = []
        self.response_after: list[Callable] = []
        self.request_retry: list[Callable] = []

    async def send(self, receivers: list[Callable], *args: Any, **kwargs: Any):
        """异步发送信号并依次执行所有接收器，支持同步和异步回调。

        Args:
            receivers: 回调函数列表。
            *args: 传递给接收器的位置参数。
            **kwargs: 传递给接收器的关键字参数。

        Yields:
            (receiver, result) 元组，receiver 为回调函数，result 为其返回值。
        """
        for receiver in receivers:
            if iscoroutinefunction(receiver):
                result = await receiver(*args, **kwargs)
            else:
                result = receiver(*args, **kwargs)
            yield receiver, result

    def send_sync(self, receivers: list[Callable], *args: Any, **kwargs: Any):
        """同步发送信号并依次执行所有接收器（仅支持同步回调）。

        Args:
            receivers: 回调函数列表。
            *args: 传递给接收器的位置参数。
            **kwargs: 传递给接收器的关键字参数。

        Yields:
            (receiver, result) 元组，receiver 为回调函数，result 为其返回值。
        """
        for receiver in receivers:
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
        self.request_before.append(func)
        return func

    def on_response_after(self, func: Callable) -> Callable:
        """装饰器：注册响应后中间件。

        回调函数接收 Response 参数，可返回替换的 Response。

        Args:
            func: 中间件回调函数。

        Returns:
            原函数（不做修改）。
        """
        self.response_after.append(func)
        return func

    def on_request_retry(self, func: Callable) -> Callable:
        """装饰器：注册重试中间件。

        回调函数接收触发重试的异常对象。

        Args:
            func: 中间件回调函数。

        Returns:
            原函数（不做修改）。
        """
        self.request_retry.append(func)
        return func
