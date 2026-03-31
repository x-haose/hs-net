"""函数式快捷 API —— 无需实例化客户端即可发起 HTTP 请求。

提供 8 个异步函数和 8 个同步函数，每次调用自动创建临时客户端并在请求完成后关闭。

异步用法::

    import hs_net

    resp = await hs_net.get("https://example.com")
    resp = await hs_net.post("https://api.example.com/data", json_data={"key": "value"})

同步用法::

    resp = hs_net.sync_get("https://example.com")
    resp = hs_net.sync_post("https://api.example.com/data", json_data={"key": "value"})
"""

from __future__ import annotations

from typing import Any

from hs_net.client import Net
from hs_net.response import Response
from hs_net.sync_client import SyncNet

__all__ = [
    # 异步
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    # 同步
    "sync_request",
    "sync_get",
    "sync_post",
    "sync_put",
    "sync_patch",
    "sync_delete",
    "sync_head",
    "sync_options",
]

# ===========================================================================
# 异步快捷函数
# ===========================================================================


async def request(method: str, url: str, *, engine: str | None = None, **kwargs: Any) -> Response:
    """发起异步 HTTP 请求。

    自动创建临时 ``Net`` 客户端，请求完成后关闭。适用于一次性请求场景；
    如需复用连接，请直接使用 ``Net`` 实例。

    Args:
        method: HTTP 方法（GET、POST、PUT 等）。
        url: 请求目标 URL。
        engine: HTTP 引擎名称，如 ``"httpx"``、``"aiohttp"`` 等。
            为 ``None`` 时使用默认引擎。
        **kwargs: 传递给 ``Net.request()`` 的其他参数，
            如 ``params``、``json_data``、``headers``、``timeout`` 等。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.request("GET", "https://example.com", timeout=10)
        print(resp.status_code)
    """
    client = Net(engine=engine) if engine else Net()
    try:
        return await client.request(method, url, **kwargs)
    finally:
        await client.close()


async def get(url: str, *, params: dict = None, **kwargs: Any) -> Response:
    """发起异步 GET 请求。

    Args:
        url: 请求目标 URL。
        params: URL 查询参数。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.get("https://example.com", params={"q": "python"})
        print(resp.text)
    """
    return await request("GET", url, params=params, **kwargs)


async def post(
    url: str,
    *,
    json_data: dict = None,
    form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None,
    files: dict[str, Any] | list[tuple] | None = None,
    **kwargs: Any,
) -> Response:
    """发起异步 POST 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        form_data: 表单数据。
        files: 文件上传数据。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.post("https://api.example.com", json_data={"key": "value"})
        print(resp.json())
    """
    return await request("POST", url, json_data=json_data, form_data=form_data, files=files, **kwargs)


async def put(url: str, *, json_data: dict = None, **kwargs: Any) -> Response:
    """发起异步 PUT 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.put("https://api.example.com/1", json_data={"name": "new"})
    """
    return await request("PUT", url, json_data=json_data, **kwargs)


async def patch(url: str, *, json_data: dict = None, **kwargs: Any) -> Response:
    """发起异步 PATCH 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.patch("https://api.example.com/1", json_data={"name": "updated"})
    """
    return await request("PATCH", url, json_data=json_data, **kwargs)


async def delete(url: str, **kwargs: Any) -> Response:
    """发起异步 DELETE 请求。

    Args:
        url: 请求目标 URL。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.delete("https://api.example.com/1")
    """
    return await request("DELETE", url, **kwargs)


async def head(url: str, *, params: dict = None, **kwargs: Any) -> Response:
    """发起异步 HEAD 请求。

    Args:
        url: 请求目标 URL。
        params: URL 查询参数。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.head("https://example.com")
        print(resp.status_code)
    """
    return await request("HEAD", url, params=params, **kwargs)


async def options(url: str, **kwargs: Any) -> Response:
    """发起异步 OPTIONS 请求。

    Args:
        url: 请求目标 URL。
        **kwargs: 传递给 ``request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = await hs_net.options("https://api.example.com")
    """
    return await request("OPTIONS", url, **kwargs)


# ===========================================================================
# 同步快捷函数
# ===========================================================================


def sync_request(method: str, url: str, *, engine: str | None = None, **kwargs: Any) -> Response:
    """发起同步 HTTP 请求。

    自动创建临时 ``SyncNet`` 客户端，请求完成后关闭。适用于一次性请求场景；
    如需复用连接，请直接使用 ``SyncNet`` 实例。

    Args:
        method: HTTP 方法（GET、POST、PUT 等）。
        url: 请求目标 URL。
        engine: HTTP 引擎名称，如 ``"httpx"``、``"requests"`` 等。
            为 ``None`` 时使用默认引擎。
        **kwargs: 传递给 ``SyncNet.request()`` 的其他参数，
            如 ``params``、``json_data``、``headers``、``timeout`` 等。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_request("GET", "https://example.com", timeout=10)
        print(resp.status_code)
    """
    client = SyncNet(engine=engine) if engine else SyncNet()
    try:
        return client.request(method, url, **kwargs)
    finally:
        client.close()


def sync_get(url: str, *, params: dict = None, **kwargs: Any) -> Response:
    """发起同步 GET 请求。

    Args:
        url: 请求目标 URL。
        params: URL 查询参数。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_get("https://example.com", params={"q": "python"})
        print(resp.text)
    """
    return sync_request("GET", url, params=params, **kwargs)


def sync_post(
    url: str,
    *,
    json_data: dict = None,
    form_data: dict[str, Any] | list[tuple[str, str]] | str | bytes | None = None,
    files: dict[str, Any] | list[tuple] | None = None,
    **kwargs: Any,
) -> Response:
    """发起同步 POST 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        form_data: 表单数据。
        files: 文件上传数据。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_post("https://api.example.com", json_data={"key": "value"})
        print(resp.json())
    """
    return sync_request("POST", url, json_data=json_data, form_data=form_data, files=files, **kwargs)


def sync_put(url: str, *, json_data: dict = None, **kwargs: Any) -> Response:
    """发起同步 PUT 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_put("https://api.example.com/1", json_data={"name": "new"})
    """
    return sync_request("PUT", url, json_data=json_data, **kwargs)


def sync_patch(url: str, *, json_data: dict = None, **kwargs: Any) -> Response:
    """发起同步 PATCH 请求。

    Args:
        url: 请求目标 URL。
        json_data: JSON 请求体。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_patch("https://api.example.com/1", json_data={"name": "updated"})
    """
    return sync_request("PATCH", url, json_data=json_data, **kwargs)


def sync_delete(url: str, **kwargs: Any) -> Response:
    """发起同步 DELETE 请求。

    Args:
        url: 请求目标 URL。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_delete("https://api.example.com/1")
    """
    return sync_request("DELETE", url, **kwargs)


def sync_head(url: str, *, params: dict = None, **kwargs: Any) -> Response:
    """发起同步 HEAD 请求。

    Args:
        url: 请求目标 URL。
        params: URL 查询参数。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_head("https://example.com")
        print(resp.status_code)
    """
    return sync_request("HEAD", url, params=params, **kwargs)


def sync_options(url: str, **kwargs: Any) -> Response:
    """发起同步 OPTIONS 请求。

    Args:
        url: 请求目标 URL。
        **kwargs: 传递给 ``sync_request()`` 的其他参数。

    Returns:
        Response 响应对象。

    Example::

        resp = hs_net.sync_options("https://api.example.com")
    """
    return sync_request("OPTIONS", url, **kwargs)
