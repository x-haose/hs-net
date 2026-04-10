"""
代理切换

多个代理轮换使用，switch() 切换到下一个。
支持混合不同协议的代理，所有引擎均可使用。
"""

from hs_net import EngineEnum, ProxyService, SyncNet

# 替换为你自己的代理地址，支持混合协议
PROXY_LIST = [
    "http://proxy1:8080",
    "socks5://proxy2:1080",
    "http://user:pass@proxy3:3128",
]
TEST_URL = "http://ip-api.com/json/"

# 所有支持同步的引擎
SYNC_ENGINES = [
    EngineEnum.HTTPX,
    EngineEnum.REQUESTS,
    EngineEnum.CURL_CFFI,
    EngineEnum.REQUESTS_GO,
]


def main():
    svc = ProxyService(PROXY_LIST)

    for engine in SYNC_ENGINES:
        print(f"\n--- {engine.value} ---")
        with SyncNet(proxy=svc, engine=engine, retries=0, timeout=30) as net:
            for i in range(len(PROXY_LIST)):
                resp = net.get(TEST_URL)
                print(f"  代理 {i + 1}: {resp.json_data['query']}")
                net.proxy_service.switch()


if __name__ == "__main__":
    main()
