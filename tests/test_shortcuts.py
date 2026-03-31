"""快捷函数模块的单元测试。

使用 unittest.mock 模拟 Net / SyncNet，验证快捷函数正确转发参数并始终关闭客户端。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import hs_net
from hs_net.shortcuts import (
    delete,
    get,
    head,
    options,
    post,
    put,
    request,
    sync_delete,
    sync_get,
    sync_head,
    sync_options,
    sync_patch,
    sync_post,
    sync_put,
    sync_request,
)
from hs_net.shortcuts import (
    patch as http_patch,
)

# ---------------------------------------------------------------------------
# 辅助：构建 mock 客户端
# ---------------------------------------------------------------------------

FAKE_URL = "https://example.com/api"


def _make_mock_net():
    """创建模拟的异步 Net 客户端。"""
    mock_resp = MagicMock(name="Response")
    client = AsyncMock(name="Net")
    client.request = AsyncMock(return_value=mock_resp)
    client.close = AsyncMock()
    return client, mock_resp


def _make_mock_sync_net():
    """创建模拟的同步 SyncNet 客户端。"""
    mock_resp = MagicMock(name="Response")
    client = MagicMock(name="SyncNet")
    client.request = MagicMock(return_value=mock_resp)
    client.close = MagicMock()
    return client, mock_resp


# ===========================================================================
# 异步快捷函数测试
# ===========================================================================


class TestAsyncRequest:
    """测试异步 request() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_request_forwards_method_and_url(self):
        """验证 request() 正确转发 method 和 url。"""
        client, mock_resp = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client) as mock_cls:
            resp = await request("GET", FAKE_URL)

        mock_cls.assert_called_once_with()
        client.request.assert_awaited_once_with("GET", FAKE_URL)
        client.close.assert_awaited_once()
        assert resp is mock_resp

    @pytest.mark.asyncio
    async def test_request_forwards_kwargs(self):
        """验证 request() 正确转发额外关键字参数。"""
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await request("POST", FAKE_URL, json_data={"k": "v"}, timeout=5)

        client.request.assert_awaited_once_with("POST", FAKE_URL, json_data={"k": "v"}, timeout=5)

    @pytest.mark.asyncio
    async def test_request_with_engine(self):
        """验证 engine 参数传递给 Net 构造函数。"""
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client) as mock_cls:
            await request("GET", FAKE_URL, engine="aiohttp")

        mock_cls.assert_called_once_with(engine="aiohttp")

    @pytest.mark.asyncio
    async def test_request_close_on_exception(self):
        """验证请求异常时仍然调用 close()。"""
        client, _ = _make_mock_net()
        client.request = AsyncMock(side_effect=RuntimeError("boom"))
        with patch("hs_net.shortcuts.Net", return_value=client), pytest.raises(RuntimeError, match="boom"):
            await request("GET", FAKE_URL)

        client.close.assert_awaited_once()


class TestAsyncGet:
    """测试异步 get() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_get_delegates_to_request(self):
        """验证 get() 使用 GET 方法调用 request()。"""
        client, mock_resp = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            resp = await get(FAKE_URL, params={"q": "test"})

        client.request.assert_awaited_once_with("GET", FAKE_URL, params={"q": "test"})
        assert resp is mock_resp


class TestAsyncPost:
    """测试异步 post() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_post_delegates_with_body_params(self):
        """验证 post() 正确转发 json_data、form_data、files。"""
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await post(
                FAKE_URL,
                json_data={"a": 1},
                form_data={"b": "2"},
                files={"f": b"data"},
            )

        client.request.assert_awaited_once_with(
            "POST",
            FAKE_URL,
            json_data={"a": 1},
            form_data={"b": "2"},
            files={"f": b"data"},
        )


class TestAsyncPut:
    """测试异步 put() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_put_delegates(self):
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await put(FAKE_URL, json_data={"x": 1})

        client.request.assert_awaited_once_with("PUT", FAKE_URL, json_data={"x": 1})


class TestAsyncPatch:
    """测试异步 patch() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_patch_delegates(self):
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await http_patch(FAKE_URL, json_data={"x": 2})

        client.request.assert_awaited_once_with("PATCH", FAKE_URL, json_data={"x": 2})


class TestAsyncDelete:
    """测试异步 delete() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_delete_delegates(self):
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await delete(FAKE_URL)

        client.request.assert_awaited_once_with("DELETE", FAKE_URL)


class TestAsyncHead:
    """测试异步 head() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_head_delegates(self):
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await head(FAKE_URL, params={"p": "1"})

        client.request.assert_awaited_once_with("HEAD", FAKE_URL, params={"p": "1"})


class TestAsyncOptions:
    """测试异步 options() 快捷函数。"""

    @pytest.mark.asyncio
    async def test_options_delegates(self):
        client, _ = _make_mock_net()
        with patch("hs_net.shortcuts.Net", return_value=client):
            await options(FAKE_URL)

        client.request.assert_awaited_once_with("OPTIONS", FAKE_URL)


# ===========================================================================
# 同步快捷函数测试
# ===========================================================================


class TestSyncRequest:
    """测试同步 sync_request() 快捷函数。"""

    def test_sync_request_forwards_method_and_url(self):
        """验证 sync_request() 正确转发 method 和 url。"""
        client, mock_resp = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client) as mock_cls:
            resp = sync_request("GET", FAKE_URL)

        mock_cls.assert_called_once_with()
        client.request.assert_called_once_with("GET", FAKE_URL)
        client.close.assert_called_once()
        assert resp is mock_resp

    def test_sync_request_forwards_kwargs(self):
        """验证 sync_request() 正确转发额外关键字参数。"""
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_request("POST", FAKE_URL, json_data={"k": "v"}, timeout=5)

        client.request.assert_called_once_with("POST", FAKE_URL, json_data={"k": "v"}, timeout=5)

    def test_sync_request_with_engine(self):
        """验证 engine 参数传递给 SyncNet 构造函数。"""
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client) as mock_cls:
            sync_request("GET", FAKE_URL, engine="requests")

        mock_cls.assert_called_once_with(engine="requests")

    def test_sync_request_close_on_exception(self):
        """验证请求异常时仍然调用 close()。"""
        client, _ = _make_mock_sync_net()
        client.request = MagicMock(side_effect=RuntimeError("boom"))
        with patch("hs_net.shortcuts.SyncNet", return_value=client), pytest.raises(RuntimeError, match="boom"):
            sync_request("GET", FAKE_URL)

        client.close.assert_called_once()


class TestSyncGet:
    """测试同步 sync_get() 快捷函数。"""

    def test_sync_get_delegates(self):
        client, mock_resp = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            resp = sync_get(FAKE_URL, params={"q": "test"})

        client.request.assert_called_once_with("GET", FAKE_URL, params={"q": "test"})
        assert resp is mock_resp


class TestSyncPost:
    """测试同步 sync_post() 快捷函数。"""

    def test_sync_post_delegates_with_body_params(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_post(
                FAKE_URL,
                json_data={"a": 1},
                form_data={"b": "2"},
                files={"f": b"data"},
            )

        client.request.assert_called_once_with(
            "POST",
            FAKE_URL,
            json_data={"a": 1},
            form_data={"b": "2"},
            files={"f": b"data"},
        )


class TestSyncPut:
    def test_sync_put_delegates(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_put(FAKE_URL, json_data={"x": 1})

        client.request.assert_called_once_with("PUT", FAKE_URL, json_data={"x": 1})


class TestSyncPatch:
    def test_sync_patch_delegates(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_patch(FAKE_URL, json_data={"x": 2})

        client.request.assert_called_once_with("PATCH", FAKE_URL, json_data={"x": 2})


class TestSyncDelete:
    def test_sync_delete_delegates(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_delete(FAKE_URL)

        client.request.assert_called_once_with("DELETE", FAKE_URL)


class TestSyncHead:
    def test_sync_head_delegates(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_head(FAKE_URL, params={"p": "1"})

        client.request.assert_called_once_with("HEAD", FAKE_URL, params={"p": "1"})


class TestSyncOptions:
    def test_sync_options_delegates(self):
        client, _ = _make_mock_sync_net()
        with patch("hs_net.shortcuts.SyncNet", return_value=client):
            sync_options(FAKE_URL)

        client.request.assert_called_once_with("OPTIONS", FAKE_URL)


# ===========================================================================
# 模块级导出测试
# ===========================================================================


class TestModuleExports:
    """验证所有 16 个快捷函数都可从 hs_net 顶层模块访问。"""

    ASYNC_FUNCTIONS = [
        "request",
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    ]
    SYNC_FUNCTIONS = [
        "sync_request",
        "sync_get",
        "sync_post",
        "sync_put",
        "sync_patch",
        "sync_delete",
        "sync_head",
        "sync_options",
    ]

    @pytest.mark.parametrize("name", ASYNC_FUNCTIONS + SYNC_FUNCTIONS)
    def test_function_exists_on_module(self, name: str):
        """验证 hs_net.{name} 可访问且可调用。"""
        func = getattr(hs_net, name, None)
        assert func is not None, f"hs_net.{name} 不存在"
        assert callable(func), f"hs_net.{name} 不可调用"

    @pytest.mark.parametrize("name", ASYNC_FUNCTIONS + SYNC_FUNCTIONS)
    def test_function_in_all(self, name: str):
        """验证函数在 __all__ 中导出。"""
        assert name in hs_net.__all__, f"{name} 不在 hs_net.__all__ 中"
