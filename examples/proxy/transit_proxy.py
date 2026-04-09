"""
代理链 / 中转代理

通过中转代理连接上游（如国内通过 Clash 访问海外认证代理）。
循环验证所有同步引擎均支持代理链。

链路: 引擎 -> ProxyService -> Clash(中转) -> 海外认证代理 -> 目标站
"""

from hs_net import EngineEnum, ProxyService, SyncNet

# 替换为你自己的代理地址
PROXY = "http://user:pass@overseas-proxy.com:4600"
TRANSIT = "http://127.0.0.1:7897"

# 所有支持同步的引擎
SYNC_ENGINES = [
    EngineEnum.HTTPX,
    EngineEnum.REQUESTS,
    EngineEnum.CURL_CFFI,
    EngineEnum.REQUESTS_GO,
]


def main():
    svc = ProxyService(PROXY, transit=TRANSIT)

    for engine in SYNC_ENGINES:
        with SyncNet(proxy=svc, engine=engine, retries=0, timeout=30) as net:
            resp = net.get("http://ip-api.com/json/")
            ip = resp.json_data["query"]
            print(f"{engine.value:12s} -> IP: {ip}")


if __name__ == "__main__":
    main()
