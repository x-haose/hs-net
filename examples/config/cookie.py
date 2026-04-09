"""
Cookie 管理

会话级 Cookie 自动管理，支持请求级 Cookie 合并。
"""

from hs_net import SyncNet


def main():
    with SyncNet(
        retries=0,
        cookies={"init_token": "abc123"},  # 初始 cookie
    ) as net:
        resp = net.get("https://example.com")
        print(f"会话 cookies: {net.cookies}")

        # 请求级别 cookie（与会话 cookie 合并）
        resp = net.get("https://example.com", cookies={"extra": "value"})
        print(f"请求 cookies: {resp.request_data.cookies}")


if __name__ == "__main__":
    main()
