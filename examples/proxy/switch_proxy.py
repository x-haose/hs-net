"""
代理切换

多个代理轮换使用，switch() 切换到下一个。
支持混合不同协议的代理。
"""

from hs_net import ProxyService, SyncNet

# 替换为你自己的代理地址，支持混合协议
PROXY_LIST = [
    "http://proxy1:8080",
    "socks5://proxy2:1080",
    "http://user:pass@proxy3:3128",
]
TEST_URL = "http://ip-api.com/json/"


def main():
    svc = ProxyService(PROXY_LIST)

    with SyncNet(proxy=svc, retries=0, timeout=30) as net:
        for i in range(len(PROXY_LIST)):
            resp = net.get(TEST_URL)
            print(f"代理 {i + 1}: {resp.json_data['query']}")
            net.proxy_service.switch()


if __name__ == "__main__":
    main()
