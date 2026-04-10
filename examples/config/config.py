"""
NetConfig 配置类

使用 NetConfig 统一管理配置，支持配置继承和覆盖。
优先级：请求级参数 > 构造函数参数 > NetConfig
"""

from hs_net import EngineEnum, NetConfig, SyncNet

# ==================== 基本用法 ====================


def basic_config():
    """使用 NetConfig 统一管理配置。"""
    config = NetConfig(
        engine=EngineEnum.HTTPX,
        base_url="https://example.com",
        timeout=30.0,
        retries=3,
        retry_delay=1.0,
        user_agent="chrome",
        raise_status=True,
        headers={"Accept-Language": "zh-CN"},
    )

    with SyncNet(config=config) as net:
        resp = net.get("/")  # 实际请求 https://example.com/
        print(f"Config 示例: {resp.status_code}")


# ==================== 预设配置 ====================


def preset_config():
    """使用预设配置（适合团队统一配置）。

    注意: curl_cffi 需要额外安装: pip install hs-net[curl]
    """
    my_config = NetConfig(
        engine=EngineEnum.CURL_CFFI,
        base_url="https://example.com",
        retries=5,
        user_agent="chrome",
        engine_options={"impersonate": "chrome120"},
    )

    with SyncNet(config=my_config) as net:
        resp = net.get("/")
        print(f"预设 Config: {resp.status_code}")


# ==================== 构造函数覆盖 ====================


def override_config():
    """构造函数参数优先于 config。"""
    config = NetConfig(timeout=10.0, retries=5, user_agent="chrome")

    # timeout 和 retries 被构造函数覆盖
    with SyncNet(config=config, timeout=30.0, retries=1) as net:
        resp = net.get("https://example.com")
        print(f"参数覆盖: {resp.status_code}")


# ==================== 请求级覆盖 ====================


def request_override():
    """每次请求都可以覆盖全局配置。"""
    with SyncNet(timeout=10.0, retries=0, user_agent="chrome") as net:
        resp = net.get(
            "https://example.com",
            timeout=30.0,
            user_agent="MyBot/2.0",
            headers={"X-Custom": "per-request"},
        )
        print(f"请求级覆盖: {resp.status_code}")


if __name__ == "__main__":
    print("=== 基本 Config ===")
    basic_config()

    print("\n=== 预设 Config ===")
    preset_config()

    print("\n=== 构造函数覆盖 ===")
    override_config()

    print("\n=== 请求级覆盖 ===")
    request_override()
