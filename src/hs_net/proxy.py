"""代理归一化服务，统一处理 HTTP/SOCKS/认证代理，对外暴露纯 HTTP 代理。

支持固定代理、列表轮换、自定义代理源三种模式。

用法:

    # 固定代理（隐式）
    net = Net(proxy="socks5://user:pass@host:port")

    # 列表轮换
    net = Net(proxy=ProxyService(["http://p1:port", "socks5://p2:port"]))

    # 自定义代理源
    class MyProvider(ProxyProvider):
        def get_proxy(self) -> str:
            return "socks5://1.2.3.4:1080"

    net = Net(proxy=ProxyService(provider=MyProvider()))

    # 切换代理
    net.proxy_service.switch()
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import itertools
import logging
import random  # noqa: S311
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    import httpx

logger = logging.getLogger("hs_net.proxy")


# ===========================================================================
# ProxyProvider 协议
# ===========================================================================


class ProxyProvider(ABC):
    """代理提供者协议，用户实现此接口对接自己的代理源。

    子类必须实现 :meth:`get_proxy`（同步）。如果需要异步获取代理（如调用代理池 API），
    可额外覆写 :meth:`async_get_proxy`，默认实现会回退到同步 ``get_proxy()``。
    """

    @abstractmethod
    def get_proxy(self) -> str:
        """返回一个代理地址（同步）。

        Returns:
            代理地址字符串，如 ``"socks5://host:port"``、``"http://user:pass@host:port"``。
        """
        ...

    async def async_get_proxy(self) -> str:
        """返回一个代理地址（异步）。

        默认回退到同步 :meth:`get_proxy`，对于纯计算的 Provider 无需覆写。
        需要异步 I/O（如调用代理池 API）时应覆写此方法。

        Returns:
            代理地址字符串。
        """
        return self.get_proxy()


class FixedProxyProvider(ProxyProvider):
    """固定代理提供者，始终返回同一个代理地址。

    Args:
        proxy: 代理地址字符串。
    """

    def __init__(self, proxy: str):
        self._proxy = proxy

    def get_proxy(self) -> str:
        """返回固定的代理地址。

        Returns:
            构造时传入的代理地址。
        """
        return self._proxy


class ListProxyProvider(ProxyProvider):
    """列表代理提供者，从列表中按策略选取代理。

    Args:
        proxies: 代理地址列表。
        strategy: 选取策略，``"round_robin"`` 轮询或 ``"random"`` 随机。
    """

    def __init__(self, proxies: list[str], strategy: str = "round_robin"):
        if not proxies:
            raise ValueError("代理列表不能为空")

        self._proxies = list(proxies)
        self._strategy = strategy
        self._cycle = itertools.cycle(self._proxies)

    def get_proxy(self) -> str:
        """按策略从列表中选取一个代理地址。

        Returns:
            代理地址字符串。
        """
        if self._strategy == "random":
            return random.choice(self._proxies)  # nosec B311  # noqa: S311
        return next(self._cycle)


class ApiProxyProvider(ProxyProvider):
    """代理池 API 提供者，通过 HTTP 请求从代理池获取代理地址。

    内部使用轻量的 httpx 客户端（不经过 ProxyService），支持同步和异步。

    Args:
        api_url: 代理池 API 地址。
        proxy: 访问 API 时使用的代理（如本地 Clash），不走 ProxyService。
        parser: 自定义响应解析函数，接收 httpx.Response 返回代理地址字符串。
            默认将响应体 strip 后直接作为代理地址。
        timeout: 请求超时时间（秒），默认 10。

    用法::

        # 最简单 — API 直接返回代理地址文本
        provider = ApiProxyProvider("https://api.pool.com/get")

        # 从 JSON 响应中提取
        provider = ApiProxyProvider(
            "https://api.pool.com/get",
            parser=lambda resp: resp.json()["data"]["proxy"],
        )

        # API 在墙外，需要本地 VPN 访问
        provider = ApiProxyProvider(
            "https://api.overseas-pool.com/get",
            proxy="http://127.0.0.1:7897",
        )
    """

    def __init__(
        self,
        api_url: str,
        *,
        proxy: str | None = None,
        parser: Callable[[httpx.Response], str] | None = None,
        timeout: float = 10.0,
    ):
        self._api_url = api_url
        self._proxy = proxy
        self._parser = parser
        self._timeout = timeout
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    def _ensure_sync_client(self) -> httpx.Client:
        """确保同步 httpx 客户端已初始化并返回。

        Returns:
            httpx.Client 实例。
        """
        if self._sync_client is None:
            import httpx as _httpx

            self._sync_client = _httpx.Client(
                proxy=self._proxy,
                timeout=self._timeout,
                verify=False,  # noqa: S501
            )
        return self._sync_client

    def _ensure_async_client(self) -> httpx.AsyncClient:
        """确保异步 httpx 客户端已初始化并返回。

        Returns:
            httpx.AsyncClient 实例。
        """
        if self._async_client is None:
            import httpx as _httpx

            self._async_client = _httpx.AsyncClient(
                proxy=self._proxy,
                timeout=self._timeout,
                verify=False,  # noqa: S501
            )
        return self._async_client

    def _parse_response(self, resp: httpx.Response) -> str:
        """解析响应，提取代理地址。

        Args:
            resp: httpx 响应对象。

        Returns:
            代理地址字符串。

        Raises:
            httpx.HTTPStatusError: 当响应状态码非 2xx 时抛出。
        """
        resp.raise_for_status()
        if self._parser:
            return self._parser(resp)
        return resp.text.strip()

    def get_proxy(self) -> str:
        """同步调用代理池 API 获取代理地址。

        Returns:
            代理地址字符串。
        """
        client = self._ensure_sync_client()
        resp = client.get(self._api_url)
        return self._parse_response(resp)

    async def async_get_proxy(self) -> str:
        """异步调用代理池 API 获取代理地址。

        Returns:
            代理地址字符串。
        """
        client = self._ensure_async_client()
        resp = await client.get(self._api_url)
        return self._parse_response(resp)

    def close(self) -> None:
        """关闭内部 HTTP 客户端。"""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
        if self._async_client:
            # async client 需要在事件循环中关闭，这里标记为 None
            self._async_client = None

    async def async_close(self) -> None:
        """异步关闭内部 HTTP 客户端。"""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None


# ===========================================================================
# 代理地址解析
# ===========================================================================


@dataclass(frozen=True)
class _ProxyInfo:
    """代理地址的结构化信息。"""

    scheme: str
    host: str
    port: int
    username: str | None
    password: str | None


def _parse_proxy(proxy_url: str) -> _ProxyInfo:
    """解析代理 URL 为结构化信息。

    Args:
        proxy_url: 代理地址字符串，如 ``"socks5://user:pass@host:port"``。

    Returns:
        解析后的 _ProxyInfo 结构。

    Raises:
        ValueError: 当代理地址无法解析时抛出。
    """
    parsed = urlparse(proxy_url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or ""
    if not host:
        raise ValueError(f"无法解析代理地址: {proxy_url!r}")
    port = parsed.port or (1080 if "socks" in scheme else 8080)
    return _ProxyInfo(
        scheme=scheme,
        host=host,
        port=port,
        username=parsed.username,
        password=parsed.password,
    )


# ===========================================================================
# 上游连接
# ===========================================================================


async def _open_connection(
    host: str,
    port: int,
    transit_info: _ProxyInfo | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """建立 TCP 连接，有中转代理时先通过中转建立隧道。

    Args:
        host: 目标主机。
        port: 目标端口。
        transit_info: 中转代理信息，为 None 时直连。

    Returns:
        (StreamReader, StreamWriter) 元组。
    """
    if not transit_info:
        return await asyncio.open_connection(host, port)

    # 通过中转代理连接目标
    scheme = transit_info.scheme
    t_host = transit_info.host
    t_port = transit_info.port
    t_user = transit_info.username
    t_pass = transit_info.password

    if scheme in ("socks5", "socks5h"):
        return await _connect_via_socks5(t_host, t_port, host, port, t_user, t_pass)
    elif scheme in ("socks4", "socks4a"):
        return await _connect_via_socks4(t_host, t_port, host, port, t_user)
    else:
        return await _connect_via_http_proxy(t_host, t_port, host, port, t_user, t_pass)


async def _connect_via_http_proxy(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    username: str | None = None,
    password: str | None = None,
    transit_info: _ProxyInfo | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """通过 HTTP 代理建立 CONNECT 隧道。

    Args:
        proxy_host: HTTP 代理主机。
        proxy_port: HTTP 代理端口。
        target_host: 最终目标主机。
        target_port: 最终目标端口。
        username: 代理认证用户名。
        password: 代理认证密码。
        transit_info: 中转代理信息，为 None 时直连代理。

    Returns:
        (StreamReader, StreamWriter) 元组。

    Raises:
        ConnectionError: 当 CONNECT 握手失败时抛出。
    """
    reader, writer = await _open_connection(proxy_host, proxy_port, transit_info)

    connect_line = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
    headers = f"Host: {target_host}:{target_port}\r\n"

    if username and password:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers += f"Proxy-Authorization: Basic {credentials}\r\n"

    writer.write((connect_line + headers + "\r\n").encode())
    await writer.drain()

    response = await reader.readuntil(b"\r\n\r\n")
    status_line = response.split(b"\r\n")[0].decode()
    if "200" not in status_line:
        writer.close()
        raise ConnectionError(f"HTTP 代理 CONNECT 失败: {status_line}")

    return reader, writer


async def _connect_via_socks5(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    username: str | None = None,
    password: str | None = None,
    transit_info: _ProxyInfo | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """通过 SOCKS5 代理建立连接。

    Args:
        proxy_host: SOCKS5 代理主机。
        proxy_port: SOCKS5 代理端口。
        target_host: 最终目标主机。
        target_port: 最终目标端口。
        username: 代理认证用户名。
        password: 代理认证密码。
        transit_info: 中转代理信息，为 None 时直连代理。

    Returns:
        (StreamReader, StreamWriter) 元组。

    Raises:
        ConnectionError: 当 SOCKS5 握手失败时抛出。
    """
    from socksio import (
        SOCKS5AType,
        SOCKS5AuthMethod,
        SOCKS5AuthMethodsRequest,
        SOCKS5Command,
        SOCKS5CommandRequest,
        SOCKS5Connection,
        SOCKS5UsernamePasswordRequest,
    )

    reader, writer = await _open_connection(proxy_host, proxy_port, transit_info)
    conn = SOCKS5Connection()

    # 认证方法协商
    auth_methods = [SOCKS5AuthMethod.NO_AUTH_REQUIRED]
    if username and password:
        auth_methods.append(SOCKS5AuthMethod.USERNAME_PASSWORD)

    # noinspection PyCallingNonCallable
    conn.send(SOCKS5AuthMethodsRequest(auth_methods))
    writer.write(conn.data_to_send())
    await writer.drain()

    data = await reader.read(2)
    auth_reply = conn.receive_data(data)

    # 用户名密码认证
    if auth_reply.method == SOCKS5AuthMethod.USERNAME_PASSWORD:
        # noinspection PyCallingNonCallable
        conn.send(SOCKS5UsernamePasswordRequest(username.encode(), password.encode()))
        writer.write(conn.data_to_send())
        await writer.drain()
        data = await reader.read(2)
        conn.receive_data(data)

    # 发送 CONNECT 命令（使用域名类型）
    # noinspection PyCallingNonCallable
    conn.send(
        SOCKS5CommandRequest(
            SOCKS5Command.CONNECT,
            SOCKS5AType.DOMAIN_NAME,
            target_host.encode(),
            target_port,
        )
    )
    writer.write(conn.data_to_send())
    await writer.drain()

    data = await reader.read(32)
    reply = conn.receive_data(data)

    from socksio import SOCKS5ReplyCode

    if reply.reply_code != SOCKS5ReplyCode.SUCCEEDED:
        writer.close()
        raise ConnectionError(f"SOCKS5 连接失败: {reply.reply_code}")

    return reader, writer


async def _connect_via_socks4(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    username: str | None = None,
    transit_info: _ProxyInfo | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """通过 SOCKS4 代理建立连接。

    Args:
        proxy_host: SOCKS4 代理主机。
        proxy_port: SOCKS4 代理端口。
        target_host: 最终目标主机。
        target_port: 最终目标端口。
        username: SOCKS4 用户标识。
        transit_info: 中转代理信息，为 None 时直连代理。

    Returns:
        (StreamReader, StreamWriter) 元组。

    Raises:
        ConnectionError: 当 SOCKS4 握手失败时抛出。
    """
    from socksio import SOCKS4Command, SOCKS4Connection, SOCKS4Request

    reader, writer = await _open_connection(proxy_host, proxy_port, transit_info)
    conn = SOCKS4Connection(user_id=(username or "").encode())

    # noinspection PyCallingNonCallable
    conn.send(
        SOCKS4Request(  # noqa
            command=SOCKS4Command.CONNECT,
            port=target_port,
            addr=target_host.encode(),
            user_id=(username or "").encode(),
        )
    )
    writer.write(conn.data_to_send())
    await writer.drain()

    data = await reader.read(8)
    reply = conn.receive_data(data)

    from socksio import SOCKS4ReplyCode

    if reply.reply_code != SOCKS4ReplyCode.REQUEST_GRANTED:
        writer.close()
        raise ConnectionError(f"SOCKS4 连接失败: {reply.reply_code}")

    return reader, writer


async def _connect_upstream(
    proxy_info: _ProxyInfo,
    target_host: str,
    target_port: int,
    transit_info: _ProxyInfo | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """根据代理类型选择连接方式。

    Args:
        proxy_info: 上游代理信息。
        target_host: 最终目标主机。
        target_port: 最终目标端口。
        transit_info: 中转代理信息，为 None 时直连上游代理。

    Returns:
        (StreamReader, StreamWriter) 元组。
    """
    scheme = proxy_info.scheme
    host = proxy_info.host
    port = proxy_info.port
    username = proxy_info.username
    password = proxy_info.password

    if scheme in ("socks5", "socks5h"):
        return await _connect_via_socks5(host, port, target_host, target_port, username, password, transit_info)
    elif scheme in ("socks4", "socks4a"):
        return await _connect_via_socks4(host, port, target_host, target_port, username, transit_info)
    else:
        return await _connect_via_http_proxy(host, port, target_host, target_port, username, password, transit_info)


# ===========================================================================
# 本地代理服务
# ===========================================================================


async def _relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """单向字节转发。"""
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        with contextlib.suppress(Exception):
            writer.close()


class _ProxyServer:
    """异步本地 HTTP 代理服务器，内部使用。"""

    def __init__(self):
        self._proxy_info: _ProxyInfo | None = None
        self._transit_info: _ProxyInfo | None = None
        self._server: asyncio.Server | None = None
        self._port: int = 0
        self._client_tasks: set[asyncio.Task] = set()

    @property
    def port(self) -> int:
        """本地代理服务监听端口。"""
        return self._port

    def set_upstream(self, proxy_info: _ProxyInfo) -> None:
        """设置/切换上游代理。"""
        self._proxy_info = proxy_info
        logger.debug(f"代理服务上游切换: {proxy_info.scheme}://{proxy_info.host}:{proxy_info.port}")

    def set_transit(self, transit_info: _ProxyInfo | None) -> None:
        """设置中转代理。"""
        self._transit_info = transit_info
        if transit_info:
            logger.debug(f"代理服务中转: {transit_info.scheme}://{transit_info.host}:{transit_info.port}")

    async def _handle_client(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
    ) -> None:
        """处理客户端请求，支持 CONNECT 隧道和普通 HTTP 转发。

        同一个连接上可能有多个 HTTP 请求（keep-alive），循环处理。
        CONNECT 隧道建立后独占连接，不再循环。
        """
        task = asyncio.current_task()
        if task:
            self._client_tasks.add(task)
            task.add_done_callback(self._client_tasks.discard)
        try:
            while True:
                # 读请求行
                try:
                    request_line = await client_reader.readuntil(b"\r\n")
                except (asyncio.IncompleteReadError, ConnectionError):
                    break  # 客户端关闭连接

                # 读完所有 headers
                header_lines = [request_line]
                while True:
                    line = await client_reader.readuntil(b"\r\n")
                    header_lines.append(line)
                    if line == b"\r\n":
                        break

                parts = request_line.decode().strip().split()
                if len(parts) < 3:
                    client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    await client_writer.drain()
                    break

                method = parts[0]

                if method == "CONNECT":
                    # CONNECT 隧道独占连接，处理完不再循环
                    await self._handle_connect(client_reader, client_writer, parts)
                    break
                else:
                    # HTTP 转发，处理完一个请求后继续循环读下一个
                    await self._handle_http_forward(client_writer, header_lines)

        except Exception as e:
            logger.debug(f"代理连接处理异常: {e}")
            with contextlib.suppress(Exception):
                client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await client_writer.drain()
        finally:
            with contextlib.suppress(Exception):
                client_writer.close()

    async def _handle_connect(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        parts: list[str],
    ) -> None:
        """处理 CONNECT 隧道（HTTPS）。"""
        target = parts[1]
        if ":" in target:
            target_host, target_port = target.rsplit(":", 1)
            target_port = int(target_port)
        else:
            target_host = target
            target_port = 443

        # 连接上游（有中转时先通过中转）
        upstream_reader, upstream_writer = await _connect_upstream(
            self._proxy_info,
            target_host,
            target_port,
            self._transit_info,
        )

        try:
            # 告诉客户端连接已建立
            client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await client_writer.drain()

            # 双向转发
            await asyncio.gather(
                _relay(client_reader, upstream_writer),
                _relay(upstream_reader, client_writer),
            )
        finally:
            with contextlib.suppress(Exception):
                upstream_writer.close()

    async def _handle_http_forward(
        self,
        client_writer: asyncio.StreamWriter,
        header_lines: list[bytes],
    ) -> None:
        """处理单个 HTTP 请求转发，每次使用当前上游配置。"""
        proxy_info = self._proxy_info
        scheme = proxy_info.scheme

        if scheme in ("socks5", "socks5h", "socks4", "socks4a"):
            # SOCKS 上游：解析目标地址，通过 SOCKS 隧道直连目标
            request_line = header_lines[0].decode().strip()
            parts = request_line.split()
            url = urlparse(parts[1])
            target_host = url.hostname or ""
            target_port = url.port or 80

            upstream_reader, upstream_writer = await _connect_upstream(
                proxy_info, target_host, target_port, self._transit_info
            )

            # 改写请求行：绝对 URL → 相对路径
            path = url.path or "/"
            if url.query:
                path += f"?{url.query}"
            header_lines[0] = f"{parts[0]} {path} {parts[2]}\r\n".encode()
        else:
            # HTTP 上游：转发给上游代理（有中转时通过中转连接）
            upstream_reader, upstream_writer = await _open_connection(
                proxy_info.host, proxy_info.port, self._transit_info
            )

            if proxy_info.username and proxy_info.password:
                credentials = base64.b64encode(f"{proxy_info.username}:{proxy_info.password}".encode()).decode()
                header_lines.insert(-1, f"Proxy-Authorization: Basic {credentials}\r\n".encode())

        # 给上游请求注入 Connection: close，确保上游响应完就关闭连接
        header_lines = [line for line in header_lines if not (line != b"\r\n" and b"connection:" in line.lower())]
        header_lines.insert(-1, b"Connection: close\r\n")

        # 转发请求到上游
        for line in header_lines:
            upstream_writer.write(line)
        await upstream_writer.drain()

        # 读取上游完整响应并回写客户端
        try:
            while True:
                data = await upstream_reader.read(65536)
                if not data:
                    break
                client_writer.write(data)
                await client_writer.drain()
        finally:
            with contextlib.suppress(Exception):
                upstream_writer.close()

    async def start(self) -> None:
        """启动本地代理服务器。"""
        self._server = await asyncio.start_server(
            self._handle_client,
            "127.0.0.1",
            0,
        )
        addr = self._server.sockets[0].getsockname()
        self._port = addr[1]
        logger.info(f"代理服务已启动: 127.0.0.1:{self._port}")

    async def stop(self) -> None:
        """停止本地代理服务器。"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            # 取消所有 pending 的客户端连接任务
            tasks = list(self._client_tasks)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self._client_tasks.clear()
            self._server = None
            logger.info("代理服务已停止")


# ===========================================================================
# ProxyService 公开 API
# ===========================================================================


class ProxyService:
    """代理归一化服务。

    接受各种代理格式（HTTP/SOCKS/认证），对外暴露纯 HTTP 本地代理。

    Args:
        proxies: 代理地址或地址列表。
        provider: 自定义代理提供者，与 proxies 二选一。
        strategy: 列表轮换策略，``"round_robin"`` 或 ``"random"``。
        transit: 中转代理地址，用于无法直连上游代理时先通过中转。

    用法::

        # 单个代理
        svc = ProxyService("socks5://host:port")

        # 列表轮换
        svc = ProxyService(["http://p1:port", "socks5://p2:port"], strategy="random")

        # 代理链（通过 Clash 中转访问海外代理）
        svc = ProxyService("socks5://overseas:port", transit="http://127.0.0.1:7897")
    """

    def __init__(
        self,
        proxies: str | list[str] | None = None,
        *,
        provider: ProxyProvider | None = None,
        strategy: str = "round_robin",
        transit: str | None = None,
    ):
        if provider:
            self._provider = provider
        elif isinstance(proxies, str):
            self._provider = FixedProxyProvider(proxies)
        elif isinstance(proxies, list):
            self._provider = ListProxyProvider(proxies, strategy)
        else:
            raise ValueError("必须提供 proxies 或 provider 参数")

        self._transit_info = _parse_proxy(transit) if transit else None
        self._server: _ProxyServer | None = None
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def __del__(self):
        try:
            if self._started:
                self.stop()
        except Exception:  # nosec B110
            pass

    @property
    def provider(self) -> ProxyProvider:
        """当前代理提供者。"""
        return self._provider

    @property
    def local_url(self) -> str:
        """本地代理地址，引擎使用此地址。"""
        if not self._started or not self._server:
            raise RuntimeError("ProxyService 尚未启动")
        return f"http://127.0.0.1:{self._server.port}"

    @property
    def started(self) -> bool:
        """是否已启动。"""
        return self._started

    def _init_upstream(self) -> None:
        """从 provider 同步获取代理并设置上游。"""
        proxy_url = self._provider.get_proxy()
        proxy_info = _parse_proxy(proxy_url)
        self._server.set_upstream(proxy_info)
        self._server.set_transit(self._transit_info)

    async def _async_init_upstream(self) -> None:
        """从 provider 异步获取代理并设置上游。"""
        proxy_url = await self._provider.async_get_proxy()
        proxy_info = _parse_proxy(proxy_url)
        self._server.set_upstream(proxy_info)
        self._server.set_transit(self._transit_info)

    def switch(self) -> None:
        """切换到新代理（同步，调用 provider.get_proxy()）。"""
        if not self._started:
            raise RuntimeError("ProxyService 尚未启动")
        try:
            if self._loop:
                # 同步模式（后台事件循环线程）：通过事件循环调度，确保线程安全
                future = asyncio.run_coroutine_threadsafe(self._sync_switch_in_loop(), self._loop)
                future.result(timeout=5)
            else:
                self._init_upstream()
        except Exception as e:
            raise e.with_traceback(None) from None

    async def _sync_switch_in_loop(self) -> None:
        """在后台事件循环线程中同步切换上游（供 switch() 调度）。"""
        self._init_upstream()

    async def async_switch(self) -> None:
        """切换到新代理（异步，调用 provider.async_get_proxy()）。"""
        if not self._started:
            raise RuntimeError("ProxyService 尚未启动")
        try:
            await self._async_init_upstream()
        except Exception as e:
            raise e.with_traceback(None) from None

    # ---- 异步启停 ----

    async def async_start(self) -> None:
        """在当前事件循环中启动代理服务。"""
        if self._started:
            return
        self._server = _ProxyServer()
        try:
            await self._async_init_upstream()
        except Exception as e:
            self._server = None
            raise e.with_traceback(None) from None
        await self._server.start()
        self._started = True

    async def async_stop(self) -> None:
        """停止代理服务。"""
        if not self._started:
            return
        if self._server:
            await self._server.stop()
        # 关闭 ApiProxyProvider 的异步客户端
        if isinstance(self._provider, ApiProxyProvider):
            await self._provider.async_close()
        self._started = False

    # ---- 同步启停（在后台线程跑事件循环） ----

    def start(self) -> None:
        """以同步方式启动代理服务（内部启动后台事件循环线程）。

        内部使用 threading.Event 而非 asyncio.Event，因为需要跨线程同步。
        """
        if self._started:
            return
        self._loop = asyncio.new_event_loop()
        ready = threading.Event()
        start_error: list[BaseException] = []

        def _run():
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._sync_start(ready))
                self._loop.run_forever()
            except Exception as e:
                start_error.append(e)
                ready.set()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        ready.wait(timeout=5)

        if start_error:
            self._loop = None
            self._thread = None
            raise start_error[0].with_traceback(None) from None
        if not self._started:
            self._loop = None
            self._thread = None
            raise RuntimeError("ProxyService 启动超时")

    async def _sync_start(self, ready: threading.Event) -> None:
        """后台线程的启动协程。"""
        self._server = _ProxyServer()
        self._init_upstream()
        await self._server.start()
        self._started = True
        ready.set()

    def stop(self) -> None:
        """同步停止代理服务。"""
        if not self._started:
            return
        if self._loop and self._server:
            future = asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
            future.result(timeout=5)
            # noinspection PyTypeChecker
            self._loop.call_soon_threadsafe(self._loop.stop)
        # 关闭 ApiProxyProvider 的同步客户端
        if isinstance(self._provider, ApiProxyProvider):
            self._provider.close()
        if self._thread:
            self._thread.join(timeout=5)
        self._started = False
        self._loop = None
        self._thread = None
