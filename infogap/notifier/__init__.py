"""模組三:自動化推播與通知(Auto-Notifier)。"""

from __future__ import annotations

import logging

from .telegram_notifier import TelegramNotifier
from .line_notifier import LineNotifier

logger = logging.getLogger(__name__)


def build_notifiers(notifier_cfg: dict) -> list:
    """依設定組出啟用的通知管道。一個都沒啟用時報錯,不默默空轉。"""
    notifiers = []
    tg = notifier_cfg.get("telegram", {})
    if tg.get("enabled"):
        notifiers.append(TelegramNotifier(tg["bot_token"], tg["chat_id"]))
    ln = notifier_cfg.get("line", {})
    if ln.get("enabled"):
        notifiers.append(LineNotifier(ln["channel_access_token"], ln["to_user_id"]))
    if not notifiers:
        raise RuntimeError("沒有啟用任何通知管道(config.yaml notifier.*.enabled 全為 false)")
    return notifiers


def format_opportunity(opp: dict) -> str:
    """把一筆 opportunity(DB row 轉 dict)排成人看的訊息。"""
    return (
        f"💡 {opp['name']}(潛力 {opp['score']}/100)\n"
        f"類別:{opp.get('category') or '—'}\n"
        f"來源:{opp['source']} {opp['url']}\n"
        f"利潤空間:{opp.get('est_margin') or '—'}\n"
        f"需求熱度:{opp.get('demand_note') or '—'}\n"
        f"下一步:{opp.get('next_action') or '—'}"
    )
