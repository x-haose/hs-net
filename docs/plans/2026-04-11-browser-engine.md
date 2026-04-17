# 浏览器引擎集成方案

## 背景

hs-net 当前支持 5 种 HTTP 引擎（httpx、aiohttp、curl_cffi、requests、requests_go），但不支持浏览器渲染。核心场景：过 5s 盾/瑞数拿 cookie → 切回 httpx 高速请求；验证码/滑块交互。

## 引擎特性一览

> 数据来源：各库 GitHub README + PyPI（2026-04-17 查证）

| 引擎 | 版本 | 异步 | 同步 | HTTP/2 | TLS 指纹 | SOCKS 代理 | 安装方式 | 适用场景 |
|------|------|------|------|--------|---------|------------|---------|---------|
| httpx | 0.28.1 | ✅ | ✅ | ✅ `httpx[http2]` | ❌ | ✅ `httpx[socks]` (socksio) | 默认 | 通用场景（默认） |
| aiohttp | 3.13.5 | ✅ | ❌ | ❌ | ❌ | ❌ 需第三方 `aiohttp-socks` | `[aiohttp]` | 高并发异步 |
| curl-cffi | 0.15.0 | ✅ | ✅ | ✅ (含 HTTP/3) | ✅ JA3/TLS+HTTP/2 | ✅ 原生 (含 UDP socks5) | `[curl]` | 反爬、爬虫 |
| requests | 2.33.1 | ❌ | ✅ | ❌ | ❌ | ✅ `requests[socks]` (PySocks) | `[requests]` | 简单同步脚本 |
| requests-go | 1.0.9 | ✅ | ✅ | ✅ 帧级控制 | ✅ JA3/JA4 | ✅ 硬依赖 PySocks | `[requests-go]` | 追求性能 |

> **注**：hs-net 的 `ProxyService` 归一化层（基于 socksio）可将 SOCKS4/5 代理转为本地 HTTP 代理暴露给引擎，因此在 hs-net 内**所有引擎均可使用 SOCKS 代理**，不依赖引擎自身的 SOCKS 支持。

## 设计原则

1. **一个 Net 可持有多个引擎**，生命周期跟 Net 走
2. **多个 Net 之间不共享引擎实例**
3. **统一入口**：`net.get()` 不管底层是 httpx 还是浏览器，返回值都是 Response
4. **中央 cookie 存储**：cookies 在 Net 层管理，引擎是无状态执行器
5. **浏览器引擎继承 EngineBase**：`_download()` = goto + 拿内容 + 包装 Response

## 一、多引擎管理（Net 层改造）

### 1.1 当前结构

```python
class Net:
    _engine: EngineBase          # 单引擎
    _config: NetConfig           # 单引擎配置
```

### 1.2 改造后

```python
class Net:
    _engines: dict[str, EngineBase]    # 引擎注册表，懒加载
    _current_engine_name: str          # 当前默认引擎名
    _cookie_jar: dict[str, str]        # 中央 cookie 存储
```

### 1.3 引擎生命周期

- **懒加载**：引擎在首次使用时创建，避免不必要的浏览器启动开销
- **Net.close()** 时关闭所有已创建的引擎
- **__aenter__** 时只启动 ProxyService，引擎按需创建

### 1.4 新增 API

```python
# 切换默认引擎（后续请求都走新引擎）
net.switch_engine("ruyipage")

# 请求级指定引擎（不影响默认）
resp = await net.get(url, engine="ruyipage")

# 浏览器交互模式（借 page，出作用域还回 tab 池）
async with net.browse(url) as resp:
    await resp.click("#login")
    token = await resp.evaluate("window.__TOKEN__")
```

### 1.5 引擎解析

`_get_or_create_engine(name)` 方法：
1. 检查 `_engines` 字典，已有直接返回
2. 没有则查引擎映射表创建实例
3. 浏览器引擎额外传入 `engine_options` 中对应的配置

```python
def _get_or_create_engine(self, name: str) -> EngineBase:
    if name in self._engines:
        return self._engines[name]
    engine_cls = _resolve_async_engine_cls(name)
    engine = self._create_engine_instance(name, engine_cls)
    self._engines[name] = engine
    return engine
```

### 1.6 engine_options 扩展

当前 `engine_options` 是扁平 dict，改为支持按引擎名分组：

```python
Net(
    engine="httpx",
    engine_options={
        "http2": True,                          # httpx 专属
        "ruyipage": {                           # ruyipage 专属
            "headless": True,
            "wait_until": "networkidle",
        },
    },
)
```

解析逻辑：
- 顶层 key 如果是已知引擎名 → 对应引擎的专属配置
- 顶层 key 不是引擎名 → 当前默认引擎的配置（向后兼容）

## 二、中央 Cookie 存储

### 2.1 设计

```
Net._cookie_jar（中央）
    ↕ 每次请求前注入，响应后回收
Engine A (httpx)
Engine B (ruyipage)
```

### 2.2 流程

**请求前**：中央 jar 的 cookies 合并到 `RequestModel.cookies`（请求级 cookies 优先）

**响应后**：`Response.cookies` 合并回中央 jar（后来者覆盖）

### 2.3 实现位置

在 `_do_request()` 中处理：

```python
async def _do_request(self, data: RequestModel) -> Response:
    # 注入中央 cookies
    merged = {**self._cookie_jar, **(data.cookies or {})}
    data.cookies = merged

    # ... 发请求 ...
    resp = await engine.download(data)

    # 回收 cookies
    if resp.cookies:
        self._cookie_jar.update(resp.cookies)

    return resp
```

### 2.4 Net.cookies 属性

改为返回中央 jar 而非引擎的 cookies：

```python
@property
def cookies(self) -> dict[str, str]:
    return dict(self._cookie_jar)
```

### 2.5 向后兼容

- 初始化时 `cookies=` 参数写入中央 jar
- 不再传给引擎构造函数（引擎不持有 cookies 状态）
- 原来通过 `self._engine.cookies` 获取的逻辑，改为从中央 jar 读取

**注意**：当前 httpx 等引擎内部有自己的 cookie jar（httpx.Client 会自动管理 Set-Cookie），需要在响应后把引擎 client 的 cookies 也同步到中央 jar。具体做法是在 `build_response` 时把 `client_cookies` 带出来，在 `_do_request` 中合并。

## 三、BrowserEngineBase

### 3.1 继承关系

```
EngineBase
├── HttpxEngine
├── AiohttpEngine
├── CurlCffiEngine
├── RequestsEngine
├── RequestsGoEngine
└── BrowserEngineBase (抽象)
    ├── RuyiPageEngine
    └── PlaywrightEngine (后续)
```

### 3.2 接口定义

```python
class BrowserEngineBase(EngineBase):
    """浏览器引擎基类，继承 EngineBase 统一 _download 接口。"""

    def __init__(
        self,
        sem: Semaphore | None = None,
        headers: dict[str, Any] | None = None,
        cookies: dict | None = None,
        verify: bool = True,
        *,
        headless: bool = True,
        wait_until: str = "load",          # load | domcontentloaded | networkidle
        wait_timeout: float = 30.0,
        max_pages: int = 5,                # tab 池大小
        **engine_options: Any,
    ):
        super().__init__(sem, headers, cookies, verify, **engine_options)
        self._headless = headless
        self._wait_until = wait_until
        self._wait_timeout = wait_timeout
        self._max_pages = max_pages

    # ---- EngineBase 实现 ----

    async def _download(self, request: RequestModel) -> Response:
        """自动模式：借 tab → goto → 等待 → 拿内容 → 还 tab → 返回 Response。"""
        page = await self._acquire_page()
        try:
            await self._inject_request(page, request)     # 注入 cookies/headers/proxy
            await self._goto(page, request.url)            # 导航
            await self._wait(page, request)                # 等待页面就绪
            content = await self._get_content(page)        # 拿渲染后 HTML
            cookies = await self._get_cookies(page)        # 拿浏览器 cookies
            return build_response(
                url=await self._get_url(page),
                status_code=200,
                headers={},
                cookies=cookies,
                client_cookies=cookies,
                content=content.encode("utf-8"),
                request_data=request,
            )
        finally:
            await self._release_page(page)

    async def _stream(self, request: RequestModel) -> StreamResponse:
        """浏览器不支持流式。"""
        raise NotImplementedError("浏览器引擎不支持流式请求")

    # ---- 浏览器公共接口（手动模式）----

    @abstractmethod
    async def goto(self, page: Any, url: str, *, wait_until: str | None = None) -> None:
        """导航到指定 URL。"""
        ...

    @abstractmethod
    async def evaluate(self, page: Any, expression: str) -> Any:
        """在页面上下文中执行 JavaScript。"""
        ...

    @abstractmethod
    async def wait_for(self, page: Any, selector: str, *, timeout: float | None = None) -> None:
        """等待指定选择器出现。"""
        ...

    @abstractmethod
    async def click(self, page: Any, selector: str) -> None:
        """点击元素。"""
        ...

    @abstractmethod
    async def screenshot(self, page: Any, *, full_page: bool = False) -> bytes:
        """截图。"""
        ...

    @abstractmethod
    async def content(self, page: Any) -> str:
        """获取页面 HTML 内容。"""
        ...

    @abstractmethod
    async def get_cookies(self, page: Any) -> dict[str, str]:
        """获取页面 cookies。"""
        ...

    @abstractmethod
    async def set_cookies(self, page: Any, cookies: dict[str, str]) -> None:
        """设置页面 cookies。"""
        ...

    # ---- Tab 池（内部）----

    @abstractmethod
    async def _acquire_page(self) -> Any:
        """从 tab 池中借出一个 page。"""
        ...

    @abstractmethod
    async def _release_page(self, page: Any) -> None:
        """将 page 归还到 tab 池。"""
        ...

    # ---- 内部辅助 ----

    async def _inject_request(self, page: Any, request: RequestModel) -> None:
        """将 RequestModel 的 cookies/headers 注入到 page。"""
        if request.cookies:
            await self.set_cookies(page, request.cookies)

    async def _goto(self, page: Any, url: str) -> None:
        await self.goto(page, url, wait_until=self._wait_until)

    async def _wait(self, page: Any, request: RequestModel) -> None:
        """根据配置等待页面就绪。可被子类覆写。"""
        pass  # 默认 goto 时已等待

    async def _get_content(self, page: Any) -> str:
        return await self.content(page)

    async def _get_cookies(self, page: Any) -> dict[str, str]:
        return await self.get_cookies(page)

    async def _get_url(self, page: Any) -> str:
        """获取当前页面 URL（可能经过重定向）。"""
        ...
```

### 3.3 公共接口设计说明

所有浏览器公共方法都显式接收 `page` 参数，原因：
- **并发安全**：不存在"当前 page"的隐式状态，多个协程可以操作不同 page
- **与 tab 池配合**：page 从 acquire 到 release 的生命周期由调用方控制
- **手动模式清晰**：`BrowserResponse` 持有 page 引用，直接传给这些方法

## 四、BrowserResponse

### 4.1 继承 Response

```python
class BrowserResponse(Response):
    """浏览器引擎的响应，附带 page 引用支持进一步交互。"""

    def __init__(
        self,
        *args,
        page: Any,
        engine: BrowserEngineBase,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._page = page
        self._browser_engine = engine
        self._closed = False

    @property
    def page(self) -> Any:
        """底层 page 对象（ruyipage.Page / playwright.Page）。"""
        return self._page

    # ---- 快捷方法，代理到 engine ----

    async def evaluate(self, expression: str) -> Any:
        return await self._browser_engine.evaluate(self._page, expression)

    async def click(self, selector: str) -> None:
        await self._browser_engine.click(self._page, selector)

    async def wait_for(self, selector: str, *, timeout: float | None = None) -> None:
        await self._browser_engine.wait_for(self._page, selector, timeout=timeout)

    async def screenshot(self, *, full_page: bool = False) -> bytes:
        return await self._browser_engine.screenshot(self._page, full_page=full_page)

    async def refresh(self) -> None:
        """刷新页面并更新 content。"""
        await self._browser_engine.goto(self._page, self.url)
        html = await self._browser_engine.content(self._page)
        self.content = html.encode("utf-8")
        self._text = None
        self._selector = None

    # ---- 生命周期 ----

    async def close(self) -> None:
        """归还 page 到 tab 池。"""
        if not self._closed:
            self._closed = True
            await self._browser_engine._release_page(self._page)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
```

### 4.2 使用场景

```python
# 场景 1：过 5s 盾（自动模式，返回普通 Response）
resp = await net.get(url, engine="ruyipage")
print(resp.text)       # 渲染后的 HTML
print(resp.cookies)    # cookies 已同步到中央 jar
# tab 已自动归还，无需 close

# 场景 2：验证码交互（手动模式，返回 BrowserResponse）
async with net.browse(url) as resp:
    await resp.wait_for("#captcha-img")
    await resp.click("#slider")
    token = await resp.evaluate("window.__TOKEN__")
    print(resp.text)   # 当前页面 HTML
# 出作用域自动归还 page
```

## 五、net.browse() 方法

### 5.1 实现

```python
async def browse(
    self,
    url: str,
    *,
    engine: str = None,
    wait_until: str | None = None,
    **kwargs,
) -> BrowserResponse:
    """浏览器交互模式，返回 BrowserResponse（持有 page 引用）。

    必须通过 async with 或手动 close() 释放 page。
    """
    engine_name = engine or self._current_engine_name
    eng = self._get_or_create_engine(engine_name)

    if not isinstance(eng, BrowserEngineBase):
        raise TypeError(f"引擎 {engine_name!r} 不是浏览器引擎，无法使用 browse()")

    page = await eng._acquire_page()

    data = build_request(self._config, url=url, method="GET", **kwargs)
    # 注入中央 cookies
    merged = {**self._cookie_jar, **(data.cookies or {})}
    data.cookies = merged

    try:
        await eng._inject_request(page, data)
        await eng.goto(page, url, wait_until=wait_until or eng._wait_until)
        html = await eng.content(page)
        cookies = await eng.get_cookies(page)

        # 回收 cookies 到中央 jar
        if cookies:
            self._cookie_jar.update(cookies)

        resp = BrowserResponse(
            url=str(await eng._get_url(page)),
            status_code=200,
            headers={},
            cookies=cookies,
            client_cookies=cookies,
            content=html.encode("utf-8"),
            request_data=data,
            page=page,
            engine=eng,
        )
        return resp
    except Exception:
        await eng._release_page(page)
        raise
```

### 5.2 与 net.get(engine=) 的区别

| | `net.get(url, engine="ruyipage")` | `net.browse(url)` |
|---|---|---|
| 返回类型 | `Response` | `BrowserResponse` |
| page 生命周期 | 方法内借还，自动 | 用户管理，需 close |
| 后续交互 | 不可以 | 可以（click/evaluate/...） |
| 典型场景 | 过 5s 盾、拿 cookies | 验证码、滑块、登录流程 |

## 六、Tab 池

### 6.1 设计

在具体引擎（如 RuyiPageEngine）中实现，BrowserEngineBase 定义接口。

```python
class _TabPool:
    """tab 页池，管理浏览器 page 实例的借还。"""

    def __init__(self, browser: Any, max_pages: int = 5):
        self._browser = browser
        self._max_pages = max_pages
        self._available: asyncio.Queue[Any] = asyncio.Queue()
        self._created: int = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> Any:
        """借出一个 page，池满时等待。"""
        # 先尝试从可用池取
        try:
            return self._available.get_nowait()
        except asyncio.QueueEmpty:
            pass

        # 还有配额就创建新的
        async with self._lock:
            if self._created < self._max_pages:
                page = await self._browser.new_page()
                self._created += 1
                return page

        # 配额用完，等待归还
        return await self._available.get()

    async def release(self, page: Any) -> None:
        """归还 page（清理状态后放回池）。"""
        try:
            # 清理 page 状态：导航到 about:blank、清 cookies
            await page.goto("about:blank")
        except Exception:
            # page 已损坏，丢弃并减少计数
            async with self._lock:
                self._created -= 1
            return
        await self._available.put(page)

    async def close_all(self) -> None:
        """关闭所有 page。"""
        while not self._available.empty():
            page = self._available.get_nowait()
            try:
                await page.close()
            except Exception:
                pass
        self._created = 0
```

### 6.2 与信号量的关系

EngineBase 已有信号量控制并发。tab 池 `max_pages` 和信号量 `concurrency` 独立：
- 信号量控制**请求并发数**
- tab 池控制**浏览器 tab 数**
- 通常建议 `concurrency <= max_pages`

## 七、EngineEnum 扩展

```python
class EngineEnum(str, Enum):
    HTTPX = "httpx"
    AIOHTTP = "aiohttp"
    CURL_CFFI = "curl_cffi"
    REQUESTS = "requests"
    REQUESTS_GO = "requests_go"
    # 新增
    RUYIPAGE = "ruyipage"
    PLAYWRIGHT = "playwright"   # 后续
```

引擎映射表扩展：

```python
@functools.cache
def _get_async_engine_map() -> dict[str, type[EngineBase]]:
    ...
    # 浏览器引擎延迟导入
    try:
        from hs_net.engines.ruyipage_engine import RuyiPageEngine
        engines["ruyipage"] = RuyiPageEngine
    except ImportError:
        pass
    return engines
```

## 八、可选依赖

```toml
[project.optional-dependencies]
ruyipage = ["ruyipage>=0.1"]
playwright = ["playwright>=1.40"]
```

## 九、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `engines/base.py` | 新增 | `BrowserEngineBase` 抽象类 |
| `engines/ruyipage_engine.py` | 新增 | RuyiPage 引擎实现 |
| `response/browser.py` | 新增 | `BrowserResponse` 类 |
| `client.py` | 修改 | 多引擎管理、中央 cookie jar、`browse()`、`switch_engine()` |
| `sync_client.py` | 修改 | 同步版本对应改造 |
| `models.py` | 修改 | `EngineEnum` 新增枚举值；`RequestModel` 新增 `engine`、`wait_until` 字段 |
| `config.py` | 修改 | `NetConfig` 适配多引擎 engine_options |
| `__init__.py` | 修改 | 导出 `BrowserEngineBase`、`BrowserResponse` |
| `pyproject.toml` | 修改 | 新增 ruyipage 可选依赖 |
| `response/__init__.py` | 修改 | 导出 `BrowserResponse` |

## 十、实现顺序

### Phase 1：基础设施
1. `BrowserEngineBase` — 抽象基类 + tab 池接口
2. `BrowserResponse` — 响应扩展
3. 中央 cookie jar — Net 层改造
4. 多引擎管理 — `_engines` 字典、`switch_engine()`、`engine=` 参数

### Phase 2：RuyiPage 引擎
5. `RuyiPageEngine` — 第一个浏览器引擎实现
6. `net.browse()` — 交互模式入口
7. 测试 + 示例

### Phase 3：完善
8. SyncNet 同步版本适配
9. Playwright 引擎（后续）

## 十一、用户使用示例

```python
import asyncio
from hs_net import Net

async def main():
    async with Net(engine="httpx") as net:
        # 1. 普通 HTTP 请求
        resp = await net.get("https://api.example.com/data")
        print(resp.json_data)

        # 2. 临时用浏览器过 5s 盾
        resp = await net.get("https://protected.site.com", engine="ruyipage")
        print(resp.text)          # 渲染后的 HTML
        # cookies 已自动同步到中央 jar

        # 3. 切回 httpx 高速请求（cookies 自动带上）
        resp = await net.get("https://protected.site.com/api/list")
        print(resp.json_data)

        # 4. 验证码交互
        async with net.browse("https://login.site.com") as resp:
            await resp.wait_for("#captcha")
            await resp.click("#slider")
            result = await resp.evaluate("document.querySelector('#token').value")
            print(result)
        # page 自动归还

        # 5. 切换默认引擎
        net.switch_engine("ruyipage")
        resp = await net.get("https://another-protected.site.com")

asyncio.run(main())
```
