# 引擎

hs-net 支持 5 种 HTTP 引擎，按需切换。

| 文件 | 说明 |
|------|------|
| [multi_engine.py](multi_engine.py) | 多引擎对比、枚举选择、引擎特定配置 |
| [streaming.py](streaming.py) | 流式下载大文件，支持多引擎 |

引擎安装：

```bash
pip install hs-net[aiohttp]      # aiohttp
pip install hs-net[curl]         # curl-cffi
pip install hs-net[requests]     # requests
pip install hs-net[requests-go]  # requests-go
pip install hs-net[all]          # 全部
```
