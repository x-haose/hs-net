"""从上游数据源生成 src/hs_net/_ua_data.py。

    uv run python scripts/gen_ua_data.py

数据源各取所长，都带 CI 自动更新：

* jnrbsn/user-agents (MIT) —— 各浏览器当前最新版，日更。版本最准，用来定 DEFAULT_USER_AGENT。
* microlinkhq/top-user-agents (MIT) —— 真实流量最常用的 100 条，日更。桌面和移动端的主要来源。
* monperrus/crawler-user-agents (MIT) —— 爬虫 UA 库，中文生态（百度/搜狗/360/字节）齐全。
* App Store lookup API —— 微信当前版本号。

生成四个池: UA_POOL（桌面浏览器）、MOBILE_POOL（移动端，按平台分）、
BOT_POOL（搜索引擎爬虫）、APP_POOL（App 内置浏览器）。桌面和移动端分开，
是因为移动端 UA 会让站点返回移动版页面 —— 那是要显式选择的，不该混进 "random"。
"""

from __future__ import annotations

import gzip
import http.client
import json
import re
import urllib.request
from pathlib import Path

OUT_FILE = Path(__file__).resolve().parent.parent / "src/hs_net/_ua_data.py"

LATEST_UA_SOURCE = "https://raw.githubusercontent.com/jnrbsn/user-agents/main/user-agents.json"
TOP_UA_SOURCE = "https://raw.githubusercontent.com/microlinkhq/top-user-agents/master/src/index.json"
BROWSER_SOURCES = [LATEST_UA_SOURCE, TOP_UA_SOURCE]
BOT_SOURCE = "https://raw.githubusercontent.com/monperrus/crawler-user-agents/master/crawler-user-agents.json"

# 锚定各浏览器的标准 UA 尾部，而不是"含 Chrome/ 就算 Chrome"。
# 后者会放进魔改浏览器（Opera/Brave）和 Electron 应用 —— 上游真实流量里就有
# "obsidian/1.12.7 Chrome/142.0.7444.265 Electron/39.8.3 Safari/537.36" 这种。
BROWSER_MARKERS = [
    ("edge", re.compile(r"Chrome/[\d.]+ Safari/[\d.]+ Edg/[\d.]+$")),
    ("firefox", re.compile(r"Gecko/[\d.]+ Firefox/[\d.]+$")),
    ("chrome", re.compile(r"Chrome/[\d.]+ Safari/[\d.]+$")),
    ("safari", re.compile(r"Version/[\d.]+ Safari/[\d.]+$")),
]
DESKTOP = ("Windows NT", "Macintosh", "X11")
MOBILE = re.compile(r"Mobile|Android|iPhone|iPad")
# 真实流量里存在多年前的浏览器，但拿来伪装只会显眼。只保留距最新这么多个大版本以内的。
KEEP_MAJORS = 15

# 移动端浏览器的标准 UA 尾部：Android Chrome/Samsung/Edge、Android Firefox、iOS Safari/Chrome
MOBILE_ENDINGS = re.compile(r"(?:Mobile Safari/[\d.]+(?: EdgA/[\d.]+)?|Mobile/\w+ Safari/[\d.]+|Firefox/[\d.]+)$")
# App 内嵌的 WebView 不是浏览器：wv 是 Android WebView，GSA 是 Google App。
# 微信同属此类，但它有独立用途，由 APP_POOL 单独提供。
MOBILE_EMBEDDED = re.compile(r"; wv\)|GSA/|MicroMessenger")
# 移动端不能沿用桌面的浏览器版本过滤 —— 同一个 iOS 池里 Safari 是 Version/26、
# Chrome 是 CriOS/150，量纲不同没法比。改用系统版本，它直接反映设备新旧。
MOBILE_MIN_OS = {"android": 10, "ios": 15}

# 只收主流搜索引擎 —— 伪装它们才可能换来放行。SEO 工具（Ahrefs/Semrush）没有这个收益。
#
# 必须用精确正则而非裸 token 匹配：上游收录了大量第三方冒充项，
# 形如 "FreshRSS/1.11.2 (...) like Googlebot"、"Fake-Googlebot"、"treat like Googlebot"，
# 伪装成这些换不来任何放行。锚定标识出现在主体位置（行首或 "compatible; " 之后）才是真身。
_MAIN = r"(?:^|compatible; |; )"
BOT_PATTERNS = {
    "googlebot": rf"{_MAIN}Googlebot(?:-Mobile|-Image)?/[\d.]+",
    "bingbot": rf"{_MAIN}bingbot/[\d.]+",
    "baiduspider": rf"{_MAIN}Baiduspider(?:-render|-image)?/[\d.]+",
    "sogou": r"^Sogou [\w ]*spider/[\d.]+",
    "360spider": r"; 360Spider",
    "bytespider": r"; Bytespider",
    "yandexbot": rf"{_MAIN}YandexBot/[\d.]+",
    "duckduckbot": rf"{_MAIN}DuckDuckBot(?:-Https)?/[\d.]+",
    "applebot": rf"{_MAIN}Applebot/[\d.]+",
}

# 功能机时代的远古 bot 变体，上游有收录但今天用只会显眼
ANCIENT = re.compile(r"DoCoMo|Nokia|SAMSUNG-SGH|MIDP|UP\.Browser|MSIE [6-9]\.|Firefox/[1-9]\.|iPhone OS [1-9]_")
# 第三方工具把自己的名字塞进官方 bot 的 UA 里，伪装成它们换不来放行
PIGGYBACK = re.compile(r"seoanalyzer|SitemapProbe|probe|analyzer|monitor", re.IGNORECASE)
# 每个爬虫留几条标准形态就够，站点只认标识不认变体
MAX_PER_BOT = 2


def looks_official(ua: str) -> bool:
    """过滤上游收录的残缺/变形条目。

    上游以"能识别爬虫"为目标，收了不少畸形样本（缺右括号、缺 "+" 且带双空格），
    识别时无所谓，拿来发请求就会露馅。
    """
    return ua.count("(") == ua.count(")") and "  " not in ua and not PIGGYBACK.search(ua)


def fetch(url: str, attempts: int = 3):
    """拉取 JSON 数据源。

    必须带 User-Agent 和压缩协商：裸 urllib 请求拉 crawler-user-agents 那个
    500 KB 的文件会被 raw.githubusercontent 限速到超时，带上就是几秒的事。
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hs-net-ua-generator", "Accept-Encoding": "gzip"},
    )
    for i in range(attempts):
        try:
            # nosec B310 - URL 是本文件顶部硬编码的常量，不接受外部输入
            with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:
            if i == attempts - 1:
                raise
            print(f"  {url.rsplit('/', 1)[-1]} 第 {i + 1} 次失败({type(e).__name__})，重试")
    return None


def classify(ua: str) -> str | None:
    """判断桌面 UA 属于哪个浏览器，不合格返回 None。"""
    if MOBILE.search(ua) or not any(p in ua for p in DESKTOP):
        return None
    return next((name for name, marker in BROWSER_MARKERS if marker.search(ua)), None)


def collect_browsers() -> dict[str, list[str]]:
    """合并浏览器数据源，按浏览器分类去重，剔除过老版本。"""
    pools: dict[str, set[str]] = {name: set() for name, _ in BROWSER_MARKERS}
    for url in BROWSER_SOURCES:
        for ua in fetch(url):
            if name := classify(ua):
                pools[name].add(ua)
    result = {}
    for name, uas in pools.items():
        newest = max(version_of(ua)[0] for ua in uas)
        result[name] = sorted(ua for ua in uas if version_of(ua)[0] > newest - KEEP_MAJORS)
    return result


def classify_mobile(ua: str) -> str | None:
    """判断移动端 UA 属于哪个平台，不合格返回 None。"""
    if MOBILE_EMBEDDED.search(ua) or not MOBILE_ENDINGS.search(ua):
        return None
    if m := re.search(r"Android (\d+)", ua):
        return "android" if int(m.group(1)) >= MOBILE_MIN_OS["android"] else None
    if m := re.search(r"(?:iPhone|iPad|CPU) OS (\d+)[_.]", ua):
        return "ios" if int(m.group(1)) >= MOBILE_MIN_OS["ios"] else None
    return None


def collect_mobile() -> dict[str, list[str]]:
    """从真实流量数据里按平台收集移动端浏览器 UA。"""
    pools: dict[str, set[str]] = {name: set() for name in MOBILE_MIN_OS}
    for ua in fetch(TOP_UA_SOURCE):
        if name := classify_mobile(ua):
            pools[name].add(ua)
    return {name: sorted(uas) for name, uas in pools.items() if uas}


def clean(instance: str) -> str:
    """上游 instances 有带引号、尾随分号的脏数据。"""
    return instance.strip().strip("'\"").rstrip(";").strip()


def collect_bots() -> dict[str, list[str]]:
    """按 BOT_PATTERNS 提取爬虫 UA。

    直接扫 instances 而不按上游 pattern 分组 —— 上游 pattern 格式不统一
    （Yandex 的是 "yandex\\.com\\/bots"，根本不含 YandexBot），UA 自身才是可靠依据。
    """
    matchers = {name: re.compile(p) for name, p in BOT_PATTERNS.items()}
    pools: dict[str, set[str]] = {name: set() for name in BOT_PATTERNS}
    for rec in fetch(BOT_SOURCE):
        for raw in rec.get("instances", []):
            ua = clean(raw)
            if ANCIENT.search(ua) or not looks_official(ua):
                continue
            for name, matcher in matchers.items():
                if matcher.search(ua):
                    pools[name].add(ua)
    return {name: pick_representative(uas) for name, uas in pools.items() if pools[name]}


def pick_representative(uas: set[str]) -> list[str]:
    """挑最标准的几条：官方声明格式（compatible + 说明地址）优先，然后取最简形态。

    长的那些多是特定场景变体（移动版 Googlebot 带整串 Android 设备信息），
    不如规范形态通用。
    """
    ranked = sorted(uas, key=lambda u: (("compatible;" not in u), ("+http" not in u), len(u)))
    return sorted(ranked[:MAX_PER_BOT])


# 微信没有可抓取的 UA 数据源，但它的 UA 是严格模板，唯一真正变动的是版本号，
# 而版本号可以从 App Store 查到（com.tencent.xin），所以按模板生成。
WECHAT_APPSTORE_ID = 414478124

# 版本尾部那串 hex 的编码规律，由真实样本反推并交叉验证：
#   8.0.38 -> 0x1800262b   8.0.50 -> 0x1800323b   8.0.59 -> 0x18003b28   7.0.12 -> 0x17000c2f
# 即 [平台位|major, minor, patch, build]，iOS 平台位 0x10、Android 0x20。
# 只有末字节的内部构建号无法从版本号推导（观测值散布在 40-60），取一个观测值即可 ——
# 站点要靠它识别就得维护一张版本到构建号的映射表，现实中不存在。
_WECHAT_BUILD_BYTE = 0x39

# iOS 版本从 top-user-agents 的真实分布里取，不写死 —— 会随上游自动更新。
# NetType 两种都给，微信里 WIFI 和蜂窝网络下的 UA 确实不同。
WECHAT_IOS_TEMPLATE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS {os} like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148 MicroMessenger/{ver}({hex}) NetType/{net} Language/zh_CN"
)
WECHAT_NET_TYPES = ("WIFI", "4G")

# Android 侧没有等价数据源：设备型号、XWEB/MMWEBSDK 内核版本都拿不到，只能取观测值。
# 它们变旧不影响识别 —— 站点认的是 MicroMessenger 标识和主版本号，而主版本号是自动的。
WECHAT_ANDROID_TEMPLATE = (
    "Mozilla/5.0 (Linux; Android 14; 2406ERN9CC Build/UKQ1.240116.001; wv) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Version/4.0 Chrome/130.0.6723.107 Mobile Safari/537.36 XWEB/1300117 "
    "MMWEBSDK/20250201 MMWEBID/8080 MicroMessenger/{ver}.2820({hex}) WeChat/arm64 Weixin "
    "NetType/WIFI Language/zh_CN ABI/arm64"
)


def fetch_wechat_version() -> str:
    """从 App Store 查微信当前版本号 —— 官方、实时，无需人工维护。"""
    data = fetch(f"https://itunes.apple.com/lookup?id={WECHAT_APPSTORE_ID}&country=cn")
    return data["results"][0]["version"]


def ios_versions(top_uas: list[str]) -> list[str]:
    """从真实流量数据里取在用的 iPhone 系统版本，形如 "18_7"。"""
    found = {m.groups() for u in top_uas if (m := re.search(r"iPhone OS (\d+)_(\d+)", u))}
    return [f"{a}_{b}" for a, b in sorted(found, key=lambda t: (int(t[0]), int(t[1])))]


def wechat_hex(version: str, platform: int) -> str:
    """按 [平台位|major, minor, patch, build] 编码版本号。"""
    major, minor, patch = (int(p) for p in version.split(".")[:3])
    return f"0x{platform | major:02x}{minor:02x}{patch:02x}{_WECHAT_BUILD_BYTE:02x}"


def build_wechat_uas(version: str, os_versions: list[str]) -> list[str]:
    """按官方 UA 模板生成微信内置浏览器 UA。"""
    ios_hex, android_hex = wechat_hex(version, 0x10), wechat_hex(version, 0x20)
    uas = [
        WECHAT_IOS_TEMPLATE.format(os=os_ver, ver=version, hex=ios_hex, net=net)
        for os_ver in os_versions
        for net in WECHAT_NET_TYPES
    ]
    uas.append(WECHAT_ANDROID_TEMPLATE.format(ver=version, hex=android_hex))
    return uas


def version_of(ua: str) -> tuple[int, ...]:
    """取 UA 里的浏览器版本号，用于挑最新的一条。"""
    m = re.search(r"(?:Chrome|Firefox|Version|Edg)/([\d.]+)", ua)
    return tuple(int(p) for p in m.group(1).split(".") if p.isdigit()) if m else ()


def render(name: str, pools: dict[str, list[str]]) -> str:
    """把池渲染成 Python 字面量。"""
    body = "".join(
        f"    {key!r}: (\n" + "".join(f"        {ua!r},\n" for ua in uas) + "    ),\n" for key, uas in pools.items()
    )
    return f"{name}: dict[str, tuple[str, ...]] = {{\n{body}}}\n"


def main() -> int:
    browsers = collect_browsers()
    mobile = collect_mobile()
    bots = collect_bots()
    wechat_version = fetch_wechat_version()
    os_versions = ios_versions(fetch(TOP_UA_SOURCE))
    apps = {"wechat": build_wechat_uas(wechat_version, os_versions)}

    for name, uas in browsers.items():
        print(f"  {name:12} {len(uas):3} 条")
    print()
    for name, uas in mobile.items():
        print(f"  {name:12} {len(uas):3} 条")
    print()
    for name, uas in bots.items():
        print(f"  {name:12} {len(uas):3} 条")
    print(f"\n  wechat       {len(apps['wechat'])} 条（App Store 版本 {wechat_version}，iOS {'/'.join(os_versions)}）")

    # 默认取 Windows 桌面 Chrome 的最新版本 —— 份额最大，最不显眼
    default = max((ua for ua in browsers["chrome"] if "Windows NT" in ua), key=version_of)
    print(f"\n默认 UA: {default}")

    OUT_FILE.write_text(
        '"""内置 User-Agent 数据，由 scripts/gen_ua_data.py 生成，请勿手工编辑。"""\n\n'
        "from __future__ import annotations\n\n"
        f"DEFAULT_USER_AGENT = {default!r}\n\n"
        + render("UA_POOL", browsers)
        + "\n"
        + render("MOBILE_POOL", mobile)
        + "\n"
        + render("BOT_POOL", bots)
        + "\n"
        + render("APP_POOL", apps)
    )
    print(f"\n已写入 {OUT_FILE}  ({OUT_FILE.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
