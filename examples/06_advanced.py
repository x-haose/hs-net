"""
示例 6: 高级功能

演示 NetConfig 配置类、自动重试、并发控制、错误处理等进阶用法。
"""

import asyncio

from hs_net import (
    ConnectionException,
    EngineEnum,
    EngineNotInstalled,
    Net,
    NetConfig,
    RateLimitConfig,
    RequestException,
    RetryExhausted,
    StatusException,
    SyncNet,
    TimeoutException,
)

# ==================== NetConfig 配置类 ====================


def config_example():
    """使用 NetConfig 统一管理配置。"""
    # 方式 1: 直接实例化
    config = NetConfig(
        engine=EngineEnum.HTTPX,
        base_url="https://example.com",
        timeout=30.0,
        retries=3,
        retry_delay=1.0,
        user_agent="chrome",
        verify=False,
        raise_status=True,
        headers={"Accept-Language": "zh-CN"},
    )

    with SyncNet(config=config) as net:
        resp = net.get("/")  # 实际请求 https://example.com/
        print(f"Config 示例: {resp.status_code}")

    # 方式 2: 使用预设配置实例（适合团队统一配置）
    # 注意: curl_cffi 需要额外安装: pip install hs-net[curl]
    my_config = NetConfig(
        engine=EngineEnum.CURL_CFFI,
        base_url="https://example.com",
        retries=5,
        user_agent="chrome",
        verify=False,
        engine_options={"impersonate": "chrome120"},
    )

    with SyncNet(config=my_config) as net:
        resp = net.get("/")
        print(f"预设 Config: {resp.status_code}")


# ==================== 构造函数参数覆盖 ====================


def override_example():
    """构造函数参数优先于 config。"""
    config = NetConfig(timeout=10.0, retries=5, user_agent="chrome")

    # timeout 和 retries 被构造函数覆盖
    with SyncNet(config=config, timeout=30.0, retries=1, verify=False) as net:
        resp = net.get("https://example.com")
        print(f"参数覆盖: {resp.status_code}")


# ==================== 请求级别参数覆盖 ====================


def request_override_example():
    """每次请求都可以覆盖全局配置。"""
    with SyncNet(timeout=10.0, verify=False, retries=0, user_agent="chrome") as net:
        # 这次请求使用不同的超时和 UA
        resp = net.get(
            "https://example.com",
            timeout=30.0,
            user_agent="MyBot/2.0",
            headers={"X-Custom": "per-request"},
        )
        print(f"请求级覆盖: {resp.status_code}")


# ==================== 错误处理 ====================


def error_handling_example():
    """异常处理示例。"""

    # ---------- 1. 状态码异常 ----------
    with SyncNet(verify=False, retries=0, raise_status=True) as net:
        try:
            net.get("https://example.com/nonexistent-page-12345")
        except StatusException as e:
            print(f"状态码异常: HTTP {e.code}, URL: {e.url}")

    # ---------- 2. 超时异常 ----------
    with SyncNet(verify=False, retries=0) as net:
        try:
            net.get("https://httpbin.org/delay/10", timeout=0.5)
        except TimeoutException as e:
            print(f"超时异常: timeout={e.timeout}s, URL: {e.url}")

    # ---------- 3. 连接异常 ----------
    with SyncNet(verify=False, retries=0) as net:
        try:
            net.get("https://this-domain-does-not-exist-12345.com")
        except ConnectionException as e:
            print(f"连接异常: {e.url}")

    # ---------- 4. 重试耗尽异常 ----------
    with SyncNet(verify=False, retries=2, raise_status=True) as net:
        try:
            net.get("https://example.com/nonexistent-page-12345")
        except RetryExhausted as e:
            print(f"重试耗尽: {e.attempts} 次尝试, 最后异常: {type(e.last_exception).__name__}")

    # ---------- 5. 引擎未安装异常 ----------
    # 注意：此示例仅在未安装 curl-cffi 时触发
    # 如果已安装则正常请求不会报错
    try:
        with SyncNet(engine="curl_cffi", verify=False, retries=0) as net:
            net.get("https://example.com")
            print("curl_cffi 引擎已安装，正常运行")
    except EngineNotInstalled as e:
        print(f"引擎未安装: {e.engine_name}, 请运行: pip install {e.install_package}")

    # ---------- 6. 统一捕获所有 hs-net 异常 ----------
    with SyncNet(verify=False, retries=0, raise_status=True) as net:
        try:
            net.get("https://example.com/nonexistent-page-12345")
        except RequestException as e:
            print(f"统一异常: [{e.exception_type}] {e.exception_msg}")

    # ---------- 7. 关闭异常抛出，手动检查状态码 ----------
    with SyncNet(verify=False, retries=0, raise_status=False) as net:
        resp = net.get("https://example.com/nonexistent-page-12345")
        if not resp.ok:
            print(f"请求失败: {resp.status_code}")
        else:
            print(f"请求成功: {resp.status_code}")


# ==================== 异步并发控制 ====================


async def concurrency_example():
    """使用 concurrency 参数限制并发数。"""
    # 最多同时 3 个请求
    async with Net(verify=False, retries=0, concurrency=3) as net:
        urls = [f"https://example.com/?page={i}" for i in range(10)]

        # 并发发送 10 个请求，但同时最多 3 个
        tasks = [net.get(url) for url in urls]
        results = await asyncio.gather(*tasks)

        print(f"并发控制: {len(results)} 个请求完成")
        print(f"全部成功: {all(r.ok for r in results)}")


# ==================== 速率限制 ====================


def rate_limit_basic_example():
    """基础速率限制 — 全局每秒 N 个请求。"""
    # 最简写法：每秒最多 3 个请求
    with SyncNet(rate_limit=3, verify=False, retries=0) as net:
        for i in range(5):
            resp = net.get("https://example.com")
            print(f"  请求 {i + 1}: {resp.status_code}")


def rate_limit_per_domain_example():
    """按域名独立限速。"""
    # 不同域名使用不同的限速策略，互相独立
    with SyncNet(
        rate_limit=RateLimitConfig(
            rate=10,  # 全局默认：10 次/秒
            per_domain={
                "example.com": 2,  # example.com：2 次/秒
                "httpbin.org": RateLimitConfig(rate=1, duration=2000),  # httpbin：2 秒 1 次
            },
        ),
        verify=False,
        retries=0,
    ) as net:
        # 走域名限速（2 次/秒）
        for i in range(3):
            resp = net.get("https://example.com")
            print(f"  example.com 请求 {i + 1}: {resp.status_code}")


async def rate_limit_async_example():
    """异步速率限制 + 并发控制组合。"""
    # rate_limit 控制"每秒发多少个"，concurrency 控制"同时在跑多少个"
    async with Net(
        rate_limit=5,  # 每秒最多 5 个请求
        concurrency=3,  # 同时最多 3 个在跑
        verify=False,
        retries=0,
    ) as net:
        urls = [f"https://example.com/?page={i}" for i in range(10)]
        tasks = [net.get(url) for url in urls]
        results = await asyncio.gather(*tasks)
        print(f"  完成 {len(results)} 个请求，全部成功: {all(r.ok for r in results)}")


# ==================== 会话 Cookie 管理 ====================


def cookie_example():
    """Cookie 自动管理。"""
    with SyncNet(
        verify=False,
        retries=0,
        cookies={"init_token": "abc123"},  # 初始 cookie
    ) as net:
        resp = net.get("https://example.com")
        print(f"会话 cookies: {net.cookies}")

        # 请求级别 cookie（与会话 cookie 合并）
        resp = net.get("https://example.com", cookies={"extra": "value"})
        print(f"请求 cookies: {resp.request_data.cookies}")


if __name__ == "__main__":
    print("=== NetConfig 配置类 ===")
    config_example()

    print("\n=== 构造函数参数覆盖 ===")
    override_example()

    print("\n=== 请求级别参数覆盖 ===")
    request_override_example()

    print("\n=== 错误处理 ===")
    error_handling_example()

    print("\n=== 异步并发控制 ===")
    asyncio.run(concurrency_example())

    print("\n=== 速率限制（基础） ===")
    rate_limit_basic_example()

    print("\n=== 速率限制（按域名） ===")
    rate_limit_per_domain_example()

    print("\n=== 速率限制（异步 + 并发控制） ===")
    asyncio.run(rate_limit_async_example())

    print("\n=== Cookie 管理 ===")
    cookie_example()
