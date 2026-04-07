"""
示例 10: 可选依赖说明

hs-net 核心只依赖 httpx + tenacity，选择器和 UA 相关功能需要额外安装。

安装方式:
    pip install hs-net          # 核心: 纯 HTTP 客户端
    pip install hs-net[sp]      # 爬虫: + CSS/XPath 选择器 + JMESPath + 随机 UA
    pip install hs-net[all]     # 全部: + 所有引擎 + 爬虫功能
"""

from hs_net import SyncNet

# ==================== 核心功能（无需额外依赖） ====================


def core_features():
    """核心 HTTP 功能，只需 pip install hs-net。"""
    with SyncNet(verify=False, retries=0, user_agent="MyApp/1.0") as net:
        resp = net.get("https://example.com")

        # 基本属性
        print(f"状态码: {resp.status_code}")
        print(f"是否成功: {resp.ok}")
        print(f"域名: {resp.domain}")
        print(f"内容长度: {len(resp.content)} 字节")
        print(f"文本长度: {len(resp.text)} 字符")
        print(f"响应头: {resp.headers.get('Content-Type')}")

        # JSON 响应（内置 json.loads，不需要 jmespath）
        resp2 = net.get("https://httpbin.org/get", params={"q": "test"})
        print(f"JSON 数据: {resp2.json_data is not None}")


# ==================== 爬虫功能（需要 hs-net[sp]） ====================


def sp_features():
    """爬虫增强功能，需要 pip install hs-net[sp]。

    包含:
    - CSS/XPath 选择器 (parsel)
    - JMESPath JSON 查询 (jmespath)
    - 随机 User-Agent (fake-useragent)
    """
    # CSS 选择器
    try:
        with SyncNet(verify=False, retries=0) as net:
            resp = net.get("https://example.com")
            title = resp.css("title::text").get()
            print(f"CSS 选择器: {title}")
    except ImportError as e:
        print(f"CSS 选择器不可用: {e}")

    # JMESPath
    try:
        with SyncNet(verify=False, retries=0) as net:
            resp = net.get("https://httpbin.org/get", params={"name": "test"})
            args = resp.jmespath("args")
            print(f"JMESPath: {args}")
    except ImportError as e:
        print(f"JMESPath 不可用: {e}")

    # 随机 User-Agent
    try:
        with SyncNet(verify=False, retries=0, user_agent="random") as net:
            resp = net.get("https://httpbin.org/user-agent")
            print(f"随机 UA: {resp.json_data}")
    except ImportError as e:
        print(f"随机 UA 不可用: {e}")


if __name__ == "__main__":
    print("=== 核心功能 (pip install hs-net) ===")
    core_features()

    print("\n=== 爬虫功能 (pip install hs-net[sp]) ===")
    sp_features()
