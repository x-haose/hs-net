---
pageType: home

hero:
  name: hs-net
  text: 统一多引擎的增强型 HTTP 客户端
  tagline: 5 种引擎自由切换，内置重试、选择器、信号中间件，同步异步全支持
  actions:
    - theme: brand
      text: 快速开始
      link: /guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/x-haose/hs-net
  image:
    src: /rspress-icon.png
    alt: hs-net
features:
  - title: 多引擎切换
    details: 支持 httpx、aiohttp、curl-cffi、requests、requests-go 五种引擎，统一 API，按需安装按需切换
    icon: 🔄
  - title: 同步 & 异步
    details: Net（异步）和 SyncNet（同步）两套客户端，接口完全一致，按场景选择
    icon: ⚡
  - title: 智能选择器
    details: 内置 CSS、XPath、正则、JMESPath 四种数据提取方式，HTML 和 JSON 响应都能轻松解析
    icon: 🔍
  - title: 自动重试
    details: 基于 tenacity 的可配置重试策略，支持延迟、随机抖动，重试耗尽抛出明确异常
    icon: 🔁
  - title: 信号中间件
    details: 请求前、响应后、重试时三个钩子，实现日志、缓存、监控等横切关注点
    icon: 📡
  - title: 代理归一化
    details: 内置 ProxyService 统一处理 HTTP/SOCKS/认证代理，支持列表轮换、自定义代理源、代理链
    icon: 🌐
  - title: 速率限制
    details: 基于令牌桶的限流，支持全局和按域名独立限速，防止触发 API 限流或被封禁
    icon: ⏱️
  - title: 反爬支持
    details: curl-cffi 引擎支持浏览器 TLS 指纹模拟，配合随机 User-Agent，轻松应对反爬
    icon: 🛡️
  - title: 快捷函数
    details: await hs_net.get(url) 一行发起请求，无需实例化客户端，简单场景零配置
    icon: ✨
---
