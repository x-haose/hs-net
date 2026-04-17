# hs-net

统一多引擎的增强型 HTTP 客户端，内置重试、选择器、信号中间件，同步异步全支持。

## 特性

- **多引擎切换** — httpx、aiohttp、curl-cffi、requests、requests-go，统一 API，一行切换
- **同步 & 异步** — `Net`（异步）和 `SyncNet`（同步），接口完全一致
- **智能选择器** — 内置 CSS、XPath、正则、JMESPath 四种数据提取（可选安装）
- **流式响应** — 支持分块下载大文件，所有引擎统一接口
- **自动重试** — 基于 tenacity，可配置次数、间隔、随机抖动
- **信号中间件** — 请求前、响应后、重试时三个钩子
- **统一异常** — 超时、连接失败、状态码错误等统一映射，切换引擎不影响错误处理
- **反爬支持** — curl-cffi 浏览器 TLS 指纹模拟 + 随机 User-Agent
- **轻量核心** — 核心仅依赖 httpx + tenacity，爬虫增强按需安装

## 安装

```bash
# 核心安装（默认 httpx 引擎，仅 2 个依赖）
pip install hs-net

# 爬虫增强（CSS/XPath 选择器 + JMESPath + 随机 UA）
pip install hs-net[sp]

# 按需安装额外引擎
pip install hs-net[aiohttp]      # aiohttp 引擎
pip install hs-net[curl]         # curl-cffi 引擎（浏览器指纹模拟）
pip install hs-net[requests]     # requests 引擎
pip install hs-net[requests-go]  # requests-go 引擎
pip install hs-net[all]          # 全部引擎 + 爬虫增强
```

> Python >= 3.10。默认安装仅包含 httpx + tenacity，选择器和随机 UA 需安装 `[sp]`。

## 快速开始

### 异步

```python
import asyncio
from hs_net import Net

async def main():
    async with Net() as net:
        resp = await net.get("https://example.com")
        print(resp.text)         # 纯 HTTP 客户端，无需额外依赖
        print(resp.json_data)    # JSON 响应自动解析

asyncio.run(main())
```

### 同步

```python
from hs_net import SyncNet

with SyncNet() as net:
    resp = net.get("https://example.com")
    print(resp.status_code)  # 200
    print(resp.text[:100])   # 响应文本
```

### 数据提取（需要 `pip install hs-net[sp]`）

```python
with SyncNet() as net:
    resp = net.get("https://example.com")
    resp.css("title::text").get()               # CSS 选择器
    resp.xpath("//h1/text()").get()             # XPath
    resp.re_first(r"价格: (\d+)元")             # 正则

    resp = net.get("https://api.example.com")
    resp.jmespath("data[?age > `18`].name")     # JMESPath（JSON）
```

## 引擎对比

| 特性 | httpx | aiohttp | curl-cffi | requests | requests-go |
|------|:-----:|:-------:|:---------:|:--------:|:-----------:|
| 异步支持 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 同步支持 | ✅ | ❌ | ✅ | ✅ | ✅ |
| HTTP/2 | ✅ | ❌ | ✅ | ❌ | ✅ |
| TLS 指纹模拟 | ❌ | ❌ | ✅ | ❌ | ✅ |
| SOCKS 代理 | ✅ | ❌ | ✅ | ✅ | ✅ |
| 安装方式 | 默认 | `[aiohttp]` | `[curl]` | `[requests]` | `[requests-go]` |
| 推荐场景 | 通用首选 | 高并发 | 反爬 | 兼容老项目 | 反爬+性能 |

## 引擎切换

```python
# httpx（默认）
Net(engine="httpx")

# aiohttp
Net(engine="aiohttp")

# curl-cffi（支持浏览器指纹模拟）
Net(engine="curl_cffi", engine_options={"impersonate": "chrome120"})

# requests（仅同步）
SyncNet(engine="requests")

# requests-go
Net(engine="requests_go")
```

## 快捷函数（无需实例化）

```python
import hs_net

# 异步
resp = await hs_net.get("https://example.com")
resp = await hs_net.post("https://api.example.com/data", json_data={"key": "val"})

# 同步
resp = hs_net.sync_get("https://example.com")

# 指定引擎
resp = await hs_net.get("https://example.com", engine="curl_cffi")
```

> 快捷函数每次创建临时客户端，适合简单请求。需要复用连接、配置中间件时请使用 `Net` / `SyncNet`。

## 流式响应

分块下载大文件，不占内存：

```python
# 异步
async with Net() as net:
    resp = await net.stream("GET", "https://example.com/large-file.zip")
    async with resp:
        async for chunk in resp:
            f.write(chunk)

# 同步
with SyncNet() as net:
    with net.stream("GET", "https://example.com/large-file.zip") as resp:
        for chunk in resp:
            f.write(chunk)
```

## 配置

```python
from hs_net import Net, NetConfig

# 方式 1：构造函数参数
net = Net(
    engine="httpx",
    base_url="https://api.example.com/v1",
    timeout=30.0,
    retries=5,
    retry_delay=1.0,
    user_agent="chrome",
    proxy="http://127.0.0.1:7890",
    verify=False,
    raise_status=True,
    allow_redirects=True,
    concurrency=10,
    headers={"Accept-Language": "zh-CN"},
    cookies={"token": "abc123"},
    engine_options={"http2": True},
)

# 方式 2：NetConfig 对象
config = NetConfig(
    engine="curl_cffi",
    retries=3,
    user_agent="random",
    headers={"Authorization": "Bearer token"},
    engine_options={"impersonate": "chrome120"},
)
net = Net(config=config)
```

每次请求也可以覆盖全局配置：

```python
async with Net(timeout=10, retries=3) as net:
    # 这次请求用不同的超时、代理、UA
    resp = await net.get(
        "https://example.com",
        params={"q": "python"},
        timeout=30.0,
        proxy="http://127.0.0.1:7890",
        user_agent="MyBot/1.0",
        headers={"X-Custom": "value"},
        cookies={"session": "xyz"},
        verify=False,
        retries=5,
        retry_delay=1.0,
        raise_status=False,
        allow_redirects=True,
    )

    # POST 还支持 json_data / form_data / files
    resp = await net.post(
        "https://api.example.com/upload",
        json_data={"key": "value"},
        # form_data={"field": "value"},
        # files={"file": ("name.txt", b"content", "text/plain")},
    )
```

参数优先级：`请求方法参数 > 构造函数参数 > NetConfig 默认值`

## 信号中间件

```python
async with Net() as net:

    @net.on_request_before
    async def add_auth(req_data):
        req_data.headers["Authorization"] = "Bearer token"
        return req_data

    @net.on_response_after
    async def log_response(resp):
        print(f"{resp.status_code} {resp.url}")

    @net.on_request_retry
    async def on_retry(exc):
        print(f"重试: {exc}")

    resp = await net.get("https://example.com")
```

## 错误处理

所有引擎的异常统一映射，切换引擎不影响错误处理代码：

```python
from hs_net import (
    Net, StatusException, TimeoutException,
    ConnectionException, RetryExhausted, RequestException,
)

async with Net() as net:
    try:
        resp = await net.get("https://httpbin.org/status/404")
    except TimeoutException as e:
        print(f"超时: timeout={e.timeout}s")
    except ConnectionException as e:
        print(f"连接失败: {e.url}")
    except RetryExhausted as e:
        print(f"{e.attempts} 次重试失败: {e.last_exception}")
    except StatusException as e:
        print(f"HTTP {e.code}")
    except RequestException as e:
        print(f"请求异常: {e}")
```

## 文档

完整文档见 `docs/` 目录，本地预览：

```bash
cd docs
pnpm install
pnpm run dev
```

## License

MIT
