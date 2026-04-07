"""测试 signals.py — 信号中间件。"""

from __future__ import annotations

import pytest

from hs_net.signals import SignalManager


class TestSignalManager:
    """SignalManager 测试。"""

    def test_sync_signal(self):
        sm = SignalManager()
        results = []

        @sm.on_request_before
        def handler(data):
            results.append(f"before: {data}")
            return data

        for _receiver, _result in sm.send_sync(sm.request_before, "test_data"):
            pass

        assert results == ["before: test_data"]

    def test_sync_multiple_handlers(self):
        sm = SignalManager()
        order = []

        @sm.on_response_after
        def handler1(resp):
            order.append("h1")

        @sm.on_response_after
        def handler2(resp):
            order.append("h2")

        for _ in sm.send_sync(sm.response_after, "resp"):
            pass

        assert order == ["h1", "h2"]

    def test_retry_signal(self):
        sm = SignalManager()
        caught = []

        @sm.on_request_retry
        def on_retry(exc):
            caught.append(str(exc))

        for _ in sm.send_sync(sm.request_retry, ValueError("test error")):
            pass

        assert caught == ["test error"]

    @pytest.mark.asyncio
    async def test_async_signal(self):
        sm = SignalManager()
        results = []

        @sm.on_request_before
        async def handler(data):
            results.append(f"async: {data}")
            return data

        async for _receiver, _result in sm.send(sm.request_before, "async_data"):
            pass

        assert results == ["async: async_data"]

    @pytest.mark.asyncio
    async def test_async_mixed_handlers(self):
        sm = SignalManager()
        order = []

        @sm.on_response_after
        def sync_handler(resp):
            order.append("sync")

        @sm.on_response_after
        async def async_handler(resp):
            order.append("async")

        async for _ in sm.send(sm.response_after, "resp"):
            pass

        assert order == ["sync", "async"]

    def test_signal_isolation(self):
        """不同实例的信号互不影响。"""
        sm1 = SignalManager()
        sm2 = SignalManager()
        results = []

        @sm1.on_request_before
        def handler1(data):
            results.append("sm1")

        @sm2.on_request_before
        def handler2(data):
            results.append("sm2")

        for _ in sm1.send_sync(sm1.request_before, "test"):
            pass

        assert results == ["sm1"]

    def test_decorator_returns_original_function(self):
        sm = SignalManager()

        @sm.on_request_before
        def my_func(data):
            return data

        assert callable(my_func)
        assert my_func("hello") == "hello"
