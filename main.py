"""infogap 入口。

用法:
  python main.py fetch     只抓取(模組一)
  python main.py analyze   只分析(模組二,吃 DB 裡未分析項目)
  python main.py notify    只推播(模組三,吃 DB 裡未推播機會)
  python main.py publish   只產稿(模組四,吃 DB 裡未發布機會)
  python main.py cycle     抓→析→推 跑一輪(給 cron 用)
  python main.py loop      行程內長駐排程(每 N 分鐘一輪 + 每日產稿)
"""

from __future__ import annotations

import argparse
import logging
import sys

from infogap.config import load_config
from infogap.pipeline import run_cycle, step_analyze, step_fetch, step_notify, step_publish
from infogap.scheduler import run_forever

COMMANDS = {
    "fetch": step_fetch,
    "analyze": step_analyze,
    "notify": step_notify,
    "publish": step_publish,
    "cycle": run_cycle,
    "loop": run_forever,
}


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="資訊差監控與發布系統")
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--config", default=None, help="設定檔路徑(預設 config/config.yaml)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    COMMANDS[args.command](cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
