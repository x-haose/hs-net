"""测试 _request_builder.py — 请求构建逻辑。"""

from __future__ import annotations

from hs_net._request_builder import build_request
from hs_net.config import NetConfig


class TestBuildRequest:
    """build_request 函数测试。"""

    def test_basic_get(self):
        cfg = NetConfig()
        req = build_request(cfg, url="https://example.com", method="GET")
        assert req.url == "https://example.com"
        assert req.method == "GET"
        assert req.timeout == 20.0
        assert req.retries == 3

    def test_method_params_override_config(self):
        cfg = NetConfig(timeout=10.0, retries=5)
        req = build_request(cfg, url="https://x.com", method="GET", timeout=30.0, retries=1)
        assert req.timeout == 30.0
        assert req.retries == 1

    def test_base_url_concatenation(self):
        cfg = NetConfig(base_url="https://api.example.com/v1")

        req1 = build_request(cfg, url="/users", method="GET")
        assert req1.url == "https://api.example.com/v1/users"

        req2 = build_request(cfg, url="users", method="GET")
        assert req2.url == "https://api.example.com/v1/users"

    def test_base_url_ignored_for_absolute(self):
        cfg = NetConfig(base_url="https://api.example.com")
        req = build_request(cfg, url="https://other.com/path", method="GET")
        assert req.url == "https://other.com/path"

    def test_base_url_trailing_slash(self):
        cfg = NetConfig(base_url="https://api.example.com/v1/")
        req = build_request(cfg, url="/users", method="GET")
        assert req.url == "https://api.example.com/v1/users"

    def test_headers_merge(self):
        cfg = NetConfig(headers={"X-Global": "1"})
        req = build_request(cfg, url="https://x.com", method="GET", headers={"X-Local": "2"})
        assert req.headers["X-Global"] == "1"
        assert req.headers["X-Local"] == "2"

    def test_headers_override(self):
        cfg = NetConfig(headers={"X-Key": "old"})
        req = build_request(cfg, url="https://x.com", method="GET", headers={"X-Key": "new"})
        assert req.headers["X-Key"] == "new"

    def test_cookies_merge(self):
        cfg = NetConfig(cookies={"session": "abc"})
        req = build_request(cfg, url="https://x.com", method="GET", cookies={"token": "xyz"})
        assert req.cookies["session"] == "abc"
        assert req.cookies["token"] == "xyz"

    def test_user_agent_set(self):
        cfg = NetConfig(user_agent="chrome")
        req = build_request(cfg, url="https://x.com", method="GET")
        assert "User-Agent" in req.headers
        assert len(req.headers["User-Agent"]) > 10

    def test_user_agent_override(self):
        cfg = NetConfig(user_agent="chrome")
        req = build_request(cfg, url="https://x.com", method="GET", user_agent="MyBot/1.0")
        assert req.headers["User-Agent"] == "MyBot/1.0"

    def test_form_data_dict_encoded(self):
        cfg = NetConfig()
        req = build_request(cfg, url="https://x.com", method="POST", form_data={"a": "1", "b": "2"})
        assert isinstance(req.form_data, str)
        assert "a=1" in req.form_data
        assert "b=2" in req.form_data
        assert req.headers["Content-Type"] == "application/x-www-form-urlencoded"

    def test_form_data_string_passthrough(self):
        cfg = NetConfig()
        req = build_request(cfg, url="https://x.com", method="POST", form_data="raw=data")
        assert req.form_data == "raw=data"

    def test_form_data_not_encoded_with_files(self):
        """有 files 时 form_data 不做 urlencode。"""
        cfg = NetConfig()
        req = build_request(
            cfg,
            url="https://x.com",
            method="POST",
            form_data={"field": "value"},
            files={"file": ("a.txt", b"content")},
        )
        # form_data 保持原始 dict，交给引擎处理 multipart
        assert req.form_data == {"field": "value"}

    def test_verify_from_config(self):
        cfg = NetConfig(verify=False)
        req = build_request(cfg, url="https://x.com", method="GET")
        assert req.verify is False

    def test_verify_override(self):
        cfg = NetConfig(verify=True)
        req = build_request(cfg, url="https://x.com", method="GET", verify=False)
        assert req.verify is False

    def test_all_none_params_use_config(self):
        """所有参数为 None 时全部从 config 取值。"""
        cfg = NetConfig(
            timeout=15.0,
            retries=2,
            retry_delay=1.0,
            raise_status=False,
            allow_redirects=False,
        )
        req = build_request(cfg, url="https://x.com", method="GET")
        assert req.timeout == 15.0
        assert req.retries == 2
        assert req.retry_delay == 1.0
        assert req.raise_status is False
        assert req.allow_redirects is False
