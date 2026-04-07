"""hs-net: 统一多引擎的增强型 HTTP 客户端"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hs-net")
except PackageNotFoundError:
    __version__ = "0.0.0"

from hs_net.client import Net
from hs_net.config import NetConfig
from hs_net.exceptions import (
    ConnectionException,
    EngineNotInstalled,
    RequestException,
    RetryExhausted,
    StatusException,
    TimeoutException,
)
from hs_net.models import EngineEnum, RequestModel
from hs_net.response import Response, Selector, SelectorList, StreamResponse
from hs_net.shortcuts import (
    delete,
    get,
    head,
    options,
    patch,
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
from hs_net.sync_client import SyncNet

__all__ = [
    "Net",
    "SyncNet",
    "NetConfig",
    "EngineEnum",
    "RequestModel",
    "Response",
    "StreamResponse",
    "Selector",
    "SelectorList",
    "EngineNotInstalled",
    "RequestException",
    "StatusException",
    "TimeoutException",
    "ConnectionException",
    "RetryExhausted",
    # 异步快捷函数
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    # 同步快捷函数
    "sync_request",
    "sync_get",
    "sync_post",
    "sync_put",
    "sync_patch",
    "sync_delete",
    "sync_head",
    "sync_options",
]
