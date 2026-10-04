"""LINE 推播。

注意:LINE Notify 已於 2025-03-31 終止服務,不能再用。
這裡改用 LINE Messaging API 的 push message:
1. 在 LINE Developers Console 建 Messaging API channel,拿 channel access token。
2. 用自己的帳號加該官方帳號好友,從 webhook 事件或 Console 取得自己的 userId。
3. 免費方案每月推播則數有上限,超量要收費 — 量大時以 Telegram 為主。
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LineNotifier:
    name = "line"

    def __init__(self, channel_access_token: str, to_user_id: str, timeout: int = 15):
        self.headers = {"Authorization": f"Bearer {channel_access_token}"}
        self.to = to_user_id
        self.timeout = timeout

    def send(self, text: str) -> None:
        resp = requests.post(
            PUSH_URL,
            headers=self.headers,
            json={"to": self.to, "messages": [{"type": "text", "text": text[:5000]}]},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LINE push 失敗 HTTP {resp.status_code}: {resp.text[:300]}")
