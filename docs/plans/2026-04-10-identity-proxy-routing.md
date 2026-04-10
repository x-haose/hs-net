# ProxyService 身份路由：identity_extractor + sticky 代理绑定

## 概述

在现有 ProxyService 的域名路由基础上，新增身份路由功能。用户提供 `identity_extractor` 函数从 `RequestModel` 中提取身份标识（如 cookies、headers、URL 参数等），ProxyService 自动为每个身份从代理池分配代理并 sticky 绑定。

### 核心原理

`_do_request` 持有完整的 `RequestModel`，但 `_ProxyServer` 只能读到 TCP 字节流。通过 proxy auth（URL 的 username 字段）作为桥梁，将身份标识的哈希传递到 `_ProxyServer` 内部，实现单端口、单 server 实例的多上游路由。

### 代理选择优先级

```
身份路由（identity hash 匹配上游） → 域名路由（rules 匹配） → 默认上游代理
```

## 用户 API

```python
# 用户定义身份提取器
def my_extractor(request: RequestModel) -> str | None:
    if request.cookies and "session" in request.cookies:
        return request.cookies["session"]
    return None

# 配置 ProxyService
proxy_service = ProxyService(
    providers=[ApiProxyProvider("https://api.pool.com/get")],
    identity_extractor=my_extractor,   # 新增
)

# 使用 — 用户无感，正常写业务代码
async with Net(proxy=proxy_service) as net:
    await net.get(url, cookies={"session": "aaa"})  # → 代理 1
    await net.get(url, cookies={"session": "aaa"})  # → 同一个代理 1（sticky）
    await net.get(url, cookies={"session": "bbb"})  # → 代理 2
    await net.get(url)                               # → 默认代理
```

---

## 实现任务

### 任务 1：_ProxyServer 支持身份路由

**文件**: `src/hs_net/proxy.py` — `_ProxyServer` 类

**改动**:

1.1. 新增 `_identity_upstreams: dict[str, _ProxyInfo]` 字典，存储 identity_hash → 上游代理映射

1.2. 新增 `register_identity(identity_hash: str, proxy_info: _ProxyInfo)` 方法，注册身份与上游的绑定

1.3. 修改 `_handle_client` 方法：读取 headers 后，解析 `Proxy-Authorization` header 提取 identity_hash，传递给 `_handle_connect` 和 `_handle_http_forward`

1.4. 修改 `_handle_connect` 签名：新增 `header_lines` 参数（当前只接收 `parts`，丢失了 headers）。从 header_lines 中提取 identity_hash

1.5. 修改 `_resolve_upstream` 签名和逻辑：
```python
def _resolve_upstream(self, domain: str, identity_hash: str | None = None):
    # 1. 身份路由：identity_hash 命中 → 返回绑定的上游
    if identity_hash and identity_hash in self._identity_upstreams:
        upstream = self._identity_upstreams[identity_hash]
    else:
        upstream = self._proxy_info  # 默认上游

    # 2. 域名路由：rules 匹配则覆盖
    if self._rules:
        matched = _match_domain(domain, self._rules)
        if matched is not None:
            return matched

    return upstream
```

1.6. 新增辅助函数 `_extract_proxy_auth(header_lines: list[bytes]) -> str | None`：从 headers 中解析 `Proxy-Authorization: Basic xxx`，base64 解码后提取 username 作为 identity_hash

1.7. `_handle_http_forward` 中：转发给上游前需要 **移除** `Proxy-Authorization` header（这是给本地代理的，不是给上游的）。如果上游代理本身需要认证，已有逻辑会重新注入上游代理的认证信息

### 任务 2：ProxyService 新增 identity_extractor 和 resolve 方法

**文件**: `src/hs_net/proxy.py` — `ProxyService` 类

**改动**:

2.1. `__init__` 新增参数 `identity_extractor: Callable[[RequestModel], str | None] | None = None`

2.2. 新增 `_identity_map: dict[str, str]` 字典，存储 identity_hash → proxy_url（用于记录分配关系，便于日志和调试）

2.3. 新增 `async def resolve(self, request: RequestModel) -> str` 方法：
```python
async def resolve(self, request: RequestModel) -> str:
    """根据请求内容解析代理地址（供 Client._do_request 调用）。

    Returns:
        本地代理 URL，可能带 proxy auth 编码身份信息。
    """
    if not self._identity_extractor:
        return self.local_url

    identity = self._identity_extractor(request)
    if not identity:
        return self.local_url

    identity_hash = hashlib.md5(identity.encode()).hexdigest()

    # 已绑定 → 直接返回
    if identity_hash in self._identity_map:
        return f"http://{identity_hash}:x@127.0.0.1:{self._server.port}"

    # 首次出现 → 从 provider 分配，注册到 _ProxyServer
    proxy_url = await self._provider.async_get_proxy()
    proxy_info = _parse_proxy(proxy_url)
    self._server.register_identity(identity_hash, proxy_info)
    self._identity_map[identity_hash] = proxy_url
    logger.info(f"身份 {identity_hash[:8]}... 绑定代理: {proxy_url}")

    return f"http://{identity_hash}:x@127.0.0.1:{self._server.port}"
```

2.4. 新增同步版本 `def resolve_sync(self, request: RequestModel) -> str`：用于 SyncNet 场景，内部调用同步 `provider.get_proxy()`

2.5. 导出 `identity_extractor` 属性供外部判断是否启用身份路由

### 任务 3：Client 集成 — _do_request 调用 resolve

**文件**: `src/hs_net/client.py` — `Net` 类

**改动**:

3.1. 修改 `_do_request` 方法：在引擎发请求前，调用 `proxy_service.resolve(data)` 获取代理地址
```python
async def _do_request(self, data: RequestModel) -> Response:
    # 速率限制
    if self._rate_limiter:
        await self._rate_limiter.acquire(data.url)

    # 身份路由：解析代理地址
    if self._proxy_service and self._proxy_service.identity_extractor:
        data.proxy = await self._proxy_service.resolve(data)

    # 请求前信号 ...
```

3.2. 确认各引擎的 `download` 方法尊重 `RequestModel.proxy` 字段（per-request 代理）。如果引擎当前忽略该字段，需要补上

**文件**: `src/hs_net/sync_client.py` — `SyncNet` 类（如有同步版本需要同步改动）

### 任务 4：引擎 per-request proxy 支持检查

**文件**: `src/hs_net/engines/*.py`

**改动**:

4.1. 检查每个引擎的 `download` 方法是否使用 `RequestModel.proxy`
4.2. 对于不支持的引擎，在 `download` 中添加 per-request proxy 逻辑（将 `data.proxy` 传给底层库的对应参数）
4.3. 由于身份路由返回的是 `http://hash:x@127.0.0.1:port` 格式的本地代理 URL，引擎只需支持 HTTP 代理即可（SOCKS 归一化由 _ProxyServer 处理）

### 任务 5：__init__.py 导出更新

**文件**: `src/hs_net/__init__.py`

**改动**: 无新增公开类型需要导出。`identity_extractor` 是一个 Callable 参数，不需要额外导出

### 任务 6：测试

**文件**: `tests/test_proxy.py`

**新增测试**:

6.1. `test_identity_extractor_basic` — 基本身份提取和 sticky 绑定：同一身份返回相同代理，不同身份返回不同代理

6.2. `test_identity_extractor_none` — 提取器返回 None 时走默认代理

6.3. `test_identity_with_domain_rules` — 身份路由和域名路由共存：身份决定默认上游，域名 rules 仍然可以覆盖

6.4. `test_identity_proxy_auth_bridge` — 验证 proxy auth 桥梁：resolve 返回的 URL 包含正确的 identity_hash

6.5. `test_proxy_server_identity_upstream` — _ProxyServer 单元测试：注册身份上游后，resolve_upstream 返回正确结果

6.6. `test_identity_extractor_from_headers` — 从 headers 提取身份

6.7. `test_identity_extractor_from_url_params` — 从 URL 参数提取身份

6.8. `test_no_identity_extractor` — 未配置提取器时行为不变（兼容性）

6.9. `test_resolve_strips_proxy_auth_for_upstream` — 验证转发给上游时 Proxy-Authorization 被正确处理

### 任务 7：示例

**文件**: `examples/proxy/identity_routing.py`

**新增**: 展示身份路由的使用方式，包含从 cookies 和 headers 提取身份的示例

---

## 不改动的部分

- 域名路由（rules）— 完全不动，在 `_resolve_upstream` 内部继续生效
- ProxyProvider 体系 — 不动，identity 路由复用现有 provider 分配代理
- 本地代理服务架构 — 不动，仍然单端口单 server
- 中转代理（transit）— 不动，每个上游连接仍然可以通过中转
- 现有 API 兼容性 — 不配置 `identity_extractor` 时行为完全不变
