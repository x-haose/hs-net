# hs-net

统一多引擎的增强型 HTTP 客户端，内置重试、选择器、信号中间件，同步异步全支持。

## 特性

- **多引擎切换** — httpx、aiohttp、curl-cffi、requests、requests-go，统一 API，一行切换
- **同步 & 异步** — `Net`（异步）和 `SyncNet`（同步），接口完全一致
- **智能选择器** — 内置 CSS、XPath、正则、JMESPath 四种数据提取
- **自动重试** — 基于 tenacity，可配置次数、间隔、随机抖动
- **信号中间件** — 请求前、响应后、重试时三个钩子
- **反爬支持** — curl-cffi 浏览器 TLS 指纹模拟 + 随机 User-Agent

## 安装

```bash
pip install hs-net
```

> Python >= 3.10，所有引擎开箱即用，无需额外安装。

## 快速开始

### 异步

```python
import asyncio
from hs_net import Net

async def main():
    async with Net() as net:
        resp = await net.get("https://example.com")
        print(resp.css("title::text").get())  # Example Domain

asyncio.run(main())
```

### 同步

```python
from hs_net import SyncNet

with SyncNet() as net:
    resp = net.get("https://example.com")
    print(resp.css("title::text").get())  # Example Domain
```

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

## 数据提取

```python
resp = await net.get("https://example.com")

# CSS 选择器
resp.css("title::text").get()

# XPath
resp.xpath("//h1/text()").get()

# 正则
resp.re_first(r"价格: (\d+)元")

# JMESPath（JSON 响应）
resp = await net.get("https://api.example.com/users")
resp.jmespath("data[?age > `18`].name")
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
    verify=False,
    concurrency=10,
)

# 方式 2：NetConfig 对象
config = NetConfig(
    engine="curl_cffi",
    retries=3,
    user_agent="random",
    engine_options={"impersonate": "chrome120"},
)
net = Net(config=config)
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

```python
from hs_net import Net, StatusException, RetryExhausted, RequestException

async with Net() as net:
    try:
        resp = await net.get("https://httpbin.org/status/404")
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
