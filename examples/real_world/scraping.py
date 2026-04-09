"""
网页内容抓取

从网页中提取结构化数据。
"""

from hs_net import SyncNet


def main():
    with SyncNet(retries=2, user_agent="chrome") as net:
        resp = net.get("https://example.com")

        # 提取标题
        title = resp.css("title::text").get()
        print(f"标题: {title}")

        # 提取所有链接
        for link in resp.css("a"):
            href = link.css("::attr(href)").get()
            text = link.css("::text").get()
            print(f"链接: {text} -> {href}")

        # 提取段落文本
        paragraphs = resp.css("p::text").getall()
        for p in paragraphs:
            print(f"段落: {p}")


if __name__ == "__main__":
    main()
