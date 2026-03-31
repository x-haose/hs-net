"""测试 exceptions.py — 异常层级。"""

from __future__ import annotations

import pytest

from hs_net.exceptions import (
    ConnectionException,
    RequestException,
    RequestStatusException,
    RetryExhausted,
    StatusException,
    TimeoutException,
)


class TestExceptionHierarchy:
    """异常继承关系测试。"""

    def test_all_inherit_from_request_exception(self):
        assert issubclass(StatusException, RequestException)
        assert issubclass(TimeoutException, RequestException)
        assert issubclass(ConnectionException, RequestException)
        assert issubclass(RetryExhausted, RequestException)

    def test_backward_compat_alias(self):
        assert RequestStatusException is StatusException


class TestRequestException:
    def test_basic(self):
        exc = RequestException("TestError", "something went wrong")
        assert exc.exception_type == "TestError"
        assert exc.exception_msg == "something went wrong"
        assert "TestError" in str(exc)
        assert "something went wrong" in str(exc)

    def test_catch_as_exception(self):
        with pytest.raises(RequestException):
            raise RequestException("E", "msg")


class TestStatusException:
    def test_attributes(self):
        exc = StatusException(code=404, url="https://example.com/missing")
        assert exc.code == 404
        assert exc.url == "https://example.com/missing"
        assert "404" in str(exc)

    def test_catch_as_request_exception(self):
        with pytest.raises(RequestException):
            raise StatusException(code=500)


class TestTimeoutException:
    def test_attributes(self):
        exc = TimeoutException(url="https://slow.com", timeout=30.0)
        assert exc.url == "https://slow.com"
        assert exc.timeout == 30.0
        assert "30.0" in str(exc)


class TestConnectionException:
    def test_attributes(self):
        exc = ConnectionException(url="https://down.com", message="DNS resolution failed")
        assert exc.url == "https://down.com"
        assert "DNS resolution failed" in str(exc)


class TestRetryExhausted:
    def test_attributes(self):
        original = ValueError("original error")
        exc = RetryExhausted(attempts=3, last_exception=original, url="https://fail.com")
        assert exc.attempts == 3
        assert exc.last_exception is original
        assert exc.url == "https://fail.com"
        assert "3" in str(exc)
        assert "original error" in str(exc)

    def test_catch_as_request_exception(self):
        with pytest.raises(RequestException):
            raise RetryExhausted(attempts=1, last_exception=Exception("e"))


class TestEngineNotInstalled:
    """引擎未安装异常测试。"""

    def test_message_contains_install_command(self):
        from hs_net.exceptions import EngineNotInstalled

        exc = EngineNotInstalled("aiohttp", "hs-net[aiohttp]")
        assert "aiohttp" in str(exc)
        assert "pip install hs-net[aiohttp]" in str(exc)

    def test_attributes(self):
        from hs_net.exceptions import EngineNotInstalled

        exc = EngineNotInstalled("curl-cffi", "hs-net[curl]")
        assert exc.engine_name == "curl-cffi"
        assert exc.install_package == "hs-net[curl]"
