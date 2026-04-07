"""测试引擎解析和基础逻辑。"""

from __future__ import annotations

import pytest

from hs_net.client import _resolve_async_engine_cls
from hs_net.engines.aiohttp_engine import AiohttpEngine
from hs_net.engines.base import EngineBase, SyncEngineBase
from hs_net.engines.curl_cffi_engine import CurlCffiEngine, SyncCurlCffiEngine
from hs_net.engines.httpx_engine import HttpxEngine, SyncHttpxEngine
from hs_net.engines.requests_engine import SyncRequestsEngine
from hs_net.engines.requests_go_engine import RequestsGoEngine, SyncRequestsGoEngine
from hs_net.models import EngineEnum
from hs_net.sync_client import _resolve_sync_engine_cls


def _same_class(cls_a: type, cls_b: type) -> bool:
    """判断两个类是否为同一引擎类。

    使用限定名和模块路径比较，而非对象 identity，
    因为 importlib.reload() 会导致同一类在不同测试间产生不同的对象引用。
    """
    return cls_a.__qualname__ == cls_b.__qualname__ and cls_a.__module__ == cls_b.__module__


class TestAsyncEngineResolve:
    """异步引擎解析测试。"""

    def test_httpx(self):
        assert _same_class(_resolve_async_engine_cls("httpx"), HttpxEngine)

    def test_aiohttp(self):
        assert _same_class(_resolve_async_engine_cls("aiohttp"), AiohttpEngine)

    def test_curl_cffi(self):
        assert _same_class(_resolve_async_engine_cls("curl_cffi"), CurlCffiEngine)

    def test_requests_go(self):
        assert _same_class(_resolve_async_engine_cls("requests_go"), RequestsGoEngine)

    def test_enum(self):
        assert _same_class(_resolve_async_engine_cls(EngineEnum.HTTPX), HttpxEngine)
        assert _same_class(_resolve_async_engine_cls(EngineEnum.AIOHTTP), AiohttpEngine)

    def test_custom_engine_class(self):
        assert _resolve_async_engine_cls(HttpxEngine) is HttpxEngine

    def test_requests_raises(self):
        with pytest.raises(ValueError, match="不支持异步"):
            _resolve_async_engine_cls("requests")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="不支持"):
            _resolve_async_engine_cls("nonexistent")


class TestSyncEngineResolve:
    """同步引擎解析测试。"""

    def test_httpx(self):
        assert _same_class(_resolve_sync_engine_cls("httpx"), SyncHttpxEngine)

    def test_curl_cffi(self):
        assert _same_class(_resolve_sync_engine_cls("curl_cffi"), SyncCurlCffiEngine)

    def test_requests(self):
        assert _same_class(_resolve_sync_engine_cls("requests"), SyncRequestsEngine)

    def test_requests_go(self):
        assert _same_class(_resolve_sync_engine_cls("requests_go"), SyncRequestsGoEngine)

    def test_enum(self):
        assert _same_class(_resolve_sync_engine_cls(EngineEnum.HTTPX), SyncHttpxEngine)
        assert _same_class(_resolve_sync_engine_cls(EngineEnum.REQUESTS), SyncRequestsEngine)

    def test_custom_engine_class(self):
        assert _resolve_sync_engine_cls(SyncHttpxEngine) is SyncHttpxEngine

    def test_aiohttp_raises(self):
        with pytest.raises(ValueError, match="不支持同步"):
            _resolve_sync_engine_cls("aiohttp")

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="不支持"):
            _resolve_sync_engine_cls("nonexistent")


class TestEngineBaseClasses:
    """引擎基类结构测试。"""

    def test_async_engines_inherit_base(self):
        assert issubclass(HttpxEngine, EngineBase)
        assert issubclass(AiohttpEngine, EngineBase)
        assert issubclass(CurlCffiEngine, EngineBase)
        assert issubclass(RequestsGoEngine, EngineBase)

    def test_sync_engines_inherit_base(self):
        assert issubclass(SyncHttpxEngine, SyncEngineBase)
        assert issubclass(SyncCurlCffiEngine, SyncEngineBase)
        assert issubclass(SyncRequestsEngine, SyncEngineBase)
        assert issubclass(SyncRequestsGoEngine, SyncEngineBase)
