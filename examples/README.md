# hs-net 示例

按功能领域组织的使用示例，每个文件演示一个独立场景。

## 目录

| 目录 | 说明 |
|------|------|
| [basic/](basic/) | 基础用法 — GET 请求、HTTP 方法、快捷函数 |
| [parsing/](parsing/) | 响应解析 — CSS/XPath 选择器、JMESPath JSON 查询 |
| [middleware/](middleware/) | 中间件 — 请求前、响应后、重试、缓存 |
| [engine/](engine/) | 引擎 — 多引擎切换、流式下载 |
| [config/](config/) | 配置 — NetConfig、异常处理、并发、限速、Cookie |
| [proxy/](proxy/) | 代理 — 固定代理、代理切换、自定义源、代理链 |
| [real_world/](real_world/) | 实战 — 网页抓取、API 客户端、批量请求、反爬 |

## 快速开始

```bash
# 核心功能
pip install hs-net

# 爬虫增强（CSS/XPath + JMESPath + 随机 UA）
pip install hs-net[sp]

# 全部引擎 + 爬虫功能
pip install hs-net[all]
```

运行示例：

```bash
python examples/basic/get.py
python examples/parsing/css_xpath.py
python examples/config/error_handling.py
```
