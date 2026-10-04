"""把四個模組串成可單獨執行、也可被排程呼叫的步驟。"""

from __future__ import annotations

import logging

from . import db as dbm
from . import fetcher
from .analyzer import analyze_batch
from .config import require
from .notifier import build_notifiers, format_opportunity
from .publisher import publish_pending

logger = logging.getLogger(__name__)


def step_fetch(cfg: dict) -> None:
    conn = dbm.connect(require(cfg, "database", "path"))
    items, failures = fetcher.run_all(cfg["fetch"]["sources"], cfg["fetch"])
    inserted, skipped = dbm.insert_items(conn, items)
    logger.info("抓取完成:共 %d 筆,新增 %d、重複略過 %d", len(items), inserted, skipped)
    if failures:
        # 失效要出聲:哪些來源掛了逐一列出
        for f in failures:
            logger.error("來源失敗:%s", f)


def step_analyze(cfg: dict) -> None:
    conn = dbm.connect(require(cfg, "database", "path"))
    batch_size = cfg["analyzer"].get("batch_size", 20)
    min_score = cfg["analyzer"].get("min_score", 60)
    model = cfg["analyzer"].get("model", "claude-opus-5-5")

    rows = dbm.unanalyzed_items(conn, batch_size)
    if not rows:
        logger.info("沒有待分析項目")
        return
    items = [dict(r) for r in rows]
    opps = analyze_batch(items, model=model, min_score=min_score)
    for o in opps:
        if 0 <= o.item_index < len(items):
            dbm.insert_opportunity(conn, items[o.item_index]["id"], o.model_dump())
        else:
            logger.error("模型回了不存在的 item_index=%d,該筆丟棄", o.item_index)
    dbm.mark_analyzed(conn, [it["id"] for it in items])
    logger.info("分析完成:%d 筆輸入 → %d 個高價值機會入庫", len(items), len(opps))


def step_notify(cfg: dict) -> None:
    conn = dbm.connect(require(cfg, "database", "path"))
    pending = dbm.pending_notifications(conn)
    if not pending:
        logger.info("沒有待推播項目")
        return
    notifiers = build_notifiers(cfg["notifier"])
    sent_ids = []
    for row in pending:
        msg = format_opportunity(dict(row))
        delivered = False
        for n in notifiers:
            try:
                n.send(msg)
                delivered = True
            except Exception as exc:  # noqa: BLE001
                logger.error("%s 推播失敗:%s", n.name, exc)
        if delivered:
            sent_ids.append(row["id"])
    dbm.mark_notified(conn, sent_ids)
    logger.info("推播完成:%d 筆待送,%d 筆至少送達一個管道", len(pending), len(sent_ids))


def step_publish(cfg: dict) -> None:
    conn = dbm.connect(require(cfg, "database", "path"))
    rows = dbm.unpublished_opportunities(conn)
    result = publish_pending(
        [dict(r) for r in rows],
        output_dir=cfg["publisher"].get("output_dir", "content"),
        model=cfg["analyzer"].get("model", "claude-opus-5-5"),
    )
    if result:
        dbm.mark_published(conn, [r["id"] for r in rows])
        logger.info("發稿檔案:%s、%s(上架到 Substack/方格子仍需人工,見 README)", *result)


def run_cycle(cfg: dict) -> None:
    """一輪完整流程:抓 → 析 → 推。發布走每日排程,不在每輪裡。"""
    step_fetch(cfg)
    step_analyze(cfg)
    step_notify(cfg)
