"""测试 config.py — NetConfig 配置。"""

from __future__ import annotations

from hs_net.config import NetConfig
from hs_net.models import EngineEnum


class TestNetConfig:
    """NetConfig 默认值和自定义测试。"""

    def test_defaults(self):
        cfg = NetConfig()
        assert cfg.engine == EngineEnum.HTTPX
        assert cfg.base_url == ""
        assert cfg.timeout == 20.0
        assert cfg.retries == 3
        assert cfg.retry_delay == 0.0
        assert cfg.user_agent == "random"
        assert cfg.proxy is None
        assert cfg.verify is False
        assert cfg.raise_status is True
        assert cfg.allow_redirects is True
        assert cfg.concurrency is None
        assert cfg.headers == {}
        assert cfg.cookies == {}
        assert cfg.engine_options == {}

    def test_custom_values(self):
        cfg = NetConfig(
            engine=EngineEnum.CURL_CFFI,
            base_url="https://api.example.com",
            timeout=30.0,
            retries=5,
            verify=False,
            headers={"X-Custom": "value"},
            engine_options={"impersonate": "chrome120"},
        )
        assert cfg.engine == EngineEnum.CURL_CFFI
        assert cfg.base_url == "https://api.example.com"
        assert cfg.timeout == 30.0
        assert cfg.retries == 5
        assert cfg.verify is False
        assert cfg.headers == {"X-Custom": "value"}
        assert cfg.engine_options == {"impersonate": "chrome120"}

    def test_subclass_defaults(self):
        """通过构造参数自定义默认值。"""
        cfg = NetConfig(
            engine=EngineEnum.CURL_CFFI,
            retries=10,
            user_agent="chrome",
        )
        assert cfg.engine == EngineEnum.CURL_CFFI
        assert cfg.retries == 10
        assert cfg.user_agent == "chrome"
        # 其他保持默认
        assert cfg.timeout == 20.0

    def test_engine_string(self):
        cfg = NetConfig(engine="aiohttp")
        assert cfg.engine == "aiohttp"

    def test_independent_dict_instances(self):
        """每个实例的 headers/cookies 应独立。"""
        cfg1 = NetConfig()
        cfg2 = NetConfig()
        cfg1.headers["X-Test"] = "1"
        assert "X-Test" not in cfg2.headers
