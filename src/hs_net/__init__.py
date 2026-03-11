"""hs-net: 统一多引擎的增强型 HTTP 客户端"""

__version__ = "0.1.0"

from hs_net.client import Net
from hs_net.config import NetConfig
from hs_net.exceptions import (
    ConnectionException,
    RequestException,
    RequestStatusException,
    RetryExhausted,
    StatusException,
    TimeoutException,
)
from hs_net.models import EngineEnum, RequestModel
from hs_net.response import Response, Selector, SelectorList
from hs_net.sync_client import SyncNet

__all__ = [
    "Net",
    "SyncNet",
    "NetConfig",
    "EngineEnum",
    "RequestModel",
    "Response",
    "Selector",
    "SelectorList",
    "RequestException",
    "StatusException",
    "TimeoutException",
    "ConnectionException",
    "RetryExhausted",
    "RequestStatusException",
]
