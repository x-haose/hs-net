"""测试 models.py — EngineEnum 和 RequestModel。"""

from __future__ import annotations

import pytest

from hs_net.models import EngineEnum, RequestModel


class TestEngineEnum:
    """EngineEnum 枚举测试。"""

    def test_all_engines(self):
        assert EngineEnum.HTTPX.value == "httpx"
        assert EngineEnum.AIOHTTP.value == "aiohttp"
        assert EngineEnum.REQUESTS.value == "requests"
        assert EngineEnum.CURL_CFFI.value == "curl_cffi"
        assert EngineEnum.REQUESTS_GO.value == "requests_go"

    def test_enum_count(self):
        assert len(EngineEnum) == 5

    def test_string_comparison(self):
        assert EngineEnum.HTTPX == "httpx"
        assert EngineEnum.AIOHTTP == "aiohttp"


class TestRequestModel:
    """RequestModel Pydantic 模型测试。"""

    def test_defaults(self):
        req = RequestModel(url="https://example.com")
        assert req.method == "GET"
        assert req.raise_status is True
        assert req.allow_redirects is True
        assert req.verify is True
        assert req.headers == {}
        assert req.cookies == {}
        assert req.url_params is None
        assert req.json_data is None
        assert req.form_data is None
        assert req.files is None
        assert req.timeout is None
        assert req.retries is None
        assert req.retry_delay is None

    def test_custom_values(self):
        req = RequestModel(
            url="https://example.com/api",
            method="POST",
            json_data={"key": "value"},
            timeout=10.0,
            retries=5,
            verify=False,
        )
        assert req.method == "POST"
        assert req.json_data == {"key": "value"}
        assert req.timeout == 10.0
        assert req.retries == 5
        assert req.verify is False

    def test_form_data_types(self):
        req_dict = RequestModel(url="https://x.com", form_data={"a": "1"})
        assert req_dict.form_data == {"a": "1"}

        req_str = RequestModel(url="https://x.com", form_data="a=1&b=2")
        assert req_str.form_data == "a=1&b=2"

        req_bytes = RequestModel(url="https://x.com", form_data=b"raw")
        assert req_bytes.form_data == b"raw"

    def test_files_field(self):
        req = RequestModel(url="https://x.com", files={"file": ("a.txt", b"hello")})
        assert req.files == {"file": ("a.txt", b"hello")}

    def test_url_required(self):
        with pytest.raises(TypeError):
            RequestModel()
