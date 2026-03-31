"""测试引擎缺失时的友好报错。"""

from __future__ import annotations

import importlib
from unittest.mock import patch

import pytest

from hs_net.exceptions import EngineNotInstalled


class TestEngineNotInstalledDetection:
    """测试引擎未安装时的检测机制。"""

    def test_aiohttp_engine_raises_when_missing(self):
        """aiohttp 未安装时，实例化 AiohttpEngine 应抛出 EngineNotInstalled。"""
        with patch.dict("sys.modules", {"aiohttp": None}):
            import hs_net.engines.aiohttp_engine as mod

            importlib.reload(mod)
            with pytest.raises(EngineNotInstalled, match="aiohttp"):
                mod.AiohttpEngine()
            importlib.reload(mod)

    def test_curl_cffi_engine_raises_when_missing(self):
        """curl-cffi 未安装时，实例化引擎应抛出 EngineNotInstalled。"""
        with patch.dict(
            "sys.modules",
            {"curl_cffi": None, "curl_cffi.const": None, "curl_cffi.requests": None},
        ):
            import hs_net.engines.curl_cffi_engine as mod

            importlib.reload(mod)
            with pytest.raises(EngineNotInstalled, match="curl-cffi"):
                mod.CurlCffiEngine()
            with pytest.raises(EngineNotInstalled, match="curl-cffi"):
                mod.SyncCurlCffiEngine()
            importlib.reload(mod)

    def test_requests_engine_raises_when_missing(self):
        """requests 未安装时，实例化 SyncRequestsEngine 应抛出 EngineNotInstalled。"""
        with patch.dict("sys.modules", {"requests": None, "requests.utils": None}):
            import hs_net.engines.requests_engine as mod

            importlib.reload(mod)
            with pytest.raises(EngineNotInstalled, match="requests"):
                mod.SyncRequestsEngine()
            importlib.reload(mod)

    def test_requests_go_engine_raises_when_missing(self):
        """requests-go 未安装时，实例化引擎应抛出 EngineNotInstalled。"""
        with patch.dict("sys.modules", {"requests_go": None}):
            import hs_net.engines.requests_go_engine as mod

            importlib.reload(mod)
            with pytest.raises(EngineNotInstalled, match="requests-go"):
                mod.RequestsGoEngine()
            with pytest.raises(EngineNotInstalled, match="requests-go"):
                mod.SyncRequestsGoEngine()
            importlib.reload(mod)

    def test_install_command_in_message(self):
        """异常消息中应包含正确的安装命令。"""
        exc = EngineNotInstalled("aiohttp", "hs-net[aiohttp]")
        assert "pip install hs-net[aiohttp]" in str(exc)

        exc = EngineNotInstalled("curl-cffi", "hs-net[curl]")
        assert "pip install hs-net[curl]" in str(exc)
