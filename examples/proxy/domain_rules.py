"""
域名代理规则

按域名路由到不同代理，支持通配符匹配和直连。
未匹配的域名走默认代理。

规则格式:
    "github.com"       — 精确匹配
    "*.google.com"     — 通配符匹配（www.google.com, mail.google.com 等）
    "*.cn"             — TLD 通配符（baidu.cn, www.baidu.cn 等）
    "direct"           — 直连，不走代理

用法:
    uv run python examples/proxy/domain_rules.py
"""

import asyncio

from hs_net import Net, ProxyService

# ---- 替换为你自己的代理地址 ----
PROXY_A = "http://user:pass@proxy-host-a:port"
PROXY_B = "http://user:pass@proxy-host-b:port"

# 中转代理（如本地 Clash），不需要可设为 None
TRANSIT = None

# ---- 测试站点 ----
SITES = {
    "ip-api.com": "http://ip-api.com/json/",  # → direct
    "httpbin.org": "http://httpbin.org/ip",  # → proxy B
    "ifconfig.me": "http://ifconfig.me/ip",  # → default (proxy A)
}


async def main():
    svc = ProxyService(
        PROXY_A,  # 未匹配域名走 proxy A
        transit=TRANSIT,
        rules={
            "httpbin.org": PROXY_B,  # httpbin 走 proxy B
            "*.ip-api.com": "direct",  # ip-api 直连
        },
    )

    async with Net(proxy=svc, retries=0, timeout=30) as net:
        # 1. direct
        resp = await net.get(SITES["ip-api.com"])
        ip_direct = resp.json_data.get("query", "?")
        print(f"ip-api.com   (direct)  -> {ip_direct}")

        # 2. proxy B（rules 命中）
        resp = await net.get(SITES["httpbin.org"])
        ip_b = resp.json_data.get("origin", "?")
        print(f"httpbin.org  (proxy B) -> {ip_b}")

        # 3. proxy A（default，未命中 rules）
        resp = await net.get(SITES["ifconfig.me"])
        ip_a = resp.text.strip()
        print(f"ifconfig.me  (proxy A) -> {ip_a}")

    print()
    ips = {ip_direct, ip_a, ip_b}
    if len(ips) == 3:
        print("三个 IP 全部不同，域名路由完全生效")
    elif ip_a != ip_b:
        print("proxy A 和 proxy B IP 不同，域名路由生效")
    else:
        print("proxy A 和 proxy B IP 相同（代理池可能分配了同一个出口）")


if __name__ == "__main__":
    asyncio.run(main())
