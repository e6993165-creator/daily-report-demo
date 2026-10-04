"""定時排程:每 N 分鐘跑一輪(抓→析→推),每天固定時間產稿。

這是行程內排程(schedule 套件)。要在伺服器長駐,建議改用 cron/systemd timer
直接呼叫 `python main.py cycle` 與 `python main.py publish`,行程死了 cron 還在。
"""

from __future__ import annotations

import logging
import time

import schedule

from .pipeline import run_cycle, step_publish

logger = logging.getLogger(__name__)


def run_forever(cfg: dict) -> None:
    interval = cfg["fetch"].get("interval_minutes", 10)
    publish_hour = cfg["publisher"].get("daily_publish_hour", 8)

    def safe(fn):
        def wrapper():
            try:
                fn(cfg)
            except Exception:  # noqa: BLE001 — 單輪失敗記 log,排程不中斷
                logger.exception("排程任務失敗,下一輪照常執行")
        return wrapper

    schedule.every(interval).minutes.do(safe(run_cycle))
    schedule.every().day.at(f"{publish_hour:02d}:00").do(safe(step_publish))

    logger.info("排程啟動:每 %d 分鐘一輪,每日 %02d:00 產稿。Ctrl+C 結束。", interval, publish_hour)
    safe(run_cycle)()  # 啟動先跑一輪,不等第一個間隔
    while True:
        schedule.run_pending()
        time.sleep(5)
