# 中间件

三种信号中间件，拦截请求/响应的不同阶段。

| 文件 | 说明 |
|------|------|
| [request_before.py](request_before.py) | 请求前：添加 Header、记录日志 |
| [response_after.py](response_after.py) | 响应后：计时、统计 |
| [retry.py](retry.py) | 重试时：记录重试原因 |
| [cache.py](cache.py) | 响应缓存：相同 URL 直接返回缓存 |
