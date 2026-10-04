"""Telegram Bot 推播。

前置(一次性,人工):
1. 跟 @BotFather 建 bot,拿 bot token。
2. 對 bot 發一則訊息後,開 https://api.telegram.org/bot<token>/getUpdates 取得 chat_id。
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, timeout: int = 15):
        self.api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, text: str) -> None:
        resp = requests.post(
            self.api,
            json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            # HTTP 200 不代表送達,Telegram 的錯誤放在 body.ok / description
            raise RuntimeError(f"Telegram API 回報失敗: {body.get('description')}")
