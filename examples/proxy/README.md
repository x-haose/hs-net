# 代理

ProxyService 代理归一化服务，统一处理 HTTP/SOCKS5/认证代理。

| 文件 | 说明 |
|------|------|
| [fixed_proxy.py](fixed_proxy.py) | 固定单个代理 |
| [switch_proxy.py](switch_proxy.py) | 多代理轮换切换 |
| [custom_provider.py](custom_provider.py) | 自定义 ProxyProvider 对接代理源 |
| [api_proxy.py](api_proxy.py) | ApiProxyProvider 对接代理池 API |
| [domain_rules.py](domain_rules.py) | 域名路由规则（按域名走不同代理） |
| [transit_proxy.py](transit_proxy.py) | 代理链 / 中转代理 |
| [async_proxy.py](async_proxy.py) | 异步客户端 + 代理 |

> 运行前请替换示例中的代理地址为你自己可用的代理。
