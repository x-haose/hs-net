# 配置与控制

NetConfig 配置管理、异常处理、并发/限速控制。

| 文件 | 说明 |
|------|------|
| [config.py](config.py) | NetConfig 配置类，配置继承与覆盖 |
| [error_handling.py](error_handling.py) | 7 种异常类型及处理方式 |
| [concurrency.py](concurrency.py) | 异步并发数量控制 |
| [rate_limit.py](rate_limit.py) | 全局限速、按域名限速 |
| [cookie.py](cookie.py) | 会话 Cookie 管理 |
