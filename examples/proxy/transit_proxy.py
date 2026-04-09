"""
代理链 / 中转代理

通过中转代理连接上游（如国内通过 Clash 访问海外认证代理）。

链路: httpx -> ProxyService -> Clash(中转) -> 海外认证代理 -> 目标站
"""

from hs_net import ProxyService, SyncNet

# 替换为你自己的代理地址
PROXY = "http://user:pass@overseas-proxy.com:4600"
TRANSIT = "http://127.0.0.1:7897"


def main():
    svc = ProxyService(PROXY, transit=TRANSIT)
    with SyncNet(proxy=svc, retries=0, timeout=30) as net:
        resp = net.get("http://ip-api.com/json/")
        print(f"IP: {resp.json_data['query']}")


if __name__ == "__main__":
    main()
