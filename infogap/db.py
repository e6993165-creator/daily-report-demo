"""SQLite 暫存層。

兩張表:
  items          模組一抓回的原始項目(以 URL 的 SHA-256 去重)
  opportunities  模組二判定的高價值項目(帶推播/發布狀態)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT NOT NULL,
    title         TEXT NOT NULL,
    url           TEXT NOT NULL,
    url_hash      TEXT NOT NULL UNIQUE,
    summary       TEXT,
    published_at  TEXT,
    fetched_at    TEXT NOT NULL,
    analyzed      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_items_analyzed ON items(analyzed);

CREATE TABLE IF NOT EXISTS opportunities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER NOT NULL REFERENCES items(id),
    name          TEXT NOT NULL,
    category      TEXT,
    score         INTEGER NOT NULL,
    est_margin    TEXT,
    demand_note   TEXT,
    next_action   TEXT,
    raw_json      TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    notified      INTEGER NOT NULL DEFAULT 0,
    published     INTEGER NOT NULL DEFAULT 0
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def connect(db_path: str | Path) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_items(conn: sqlite3.Connection, items: list[dict]) -> tuple[int, int]:
    """寫入抓取結果。回傳 (新增數, 重複略過數) — 截斷/略過要可見。"""
    inserted = skipped = 0
    for it in items:
        try:
            conn.execute(
                "INSERT INTO items (source, title, url, url_hash, summary, published_at, fetched_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    it["source"], it["title"], it["url"], url_hash(it["url"]),
                    it.get("summary"), it.get("published_at"), _now(),
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    return inserted, skipped


def unanalyzed_items(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM items WHERE analyzed = 0 ORDER BY id LIMIT ?", (limit,)
    ).fetchall()


def mark_analyzed(conn: sqlite3.Connection, item_ids: list[int]) -> None:
    conn.executemany("UPDATE items SET analyzed = 1 WHERE id = ?", [(i,) for i in item_ids])
    conn.commit()


def insert_opportunity(conn: sqlite3.Connection, item_id: int, opp: dict) -> None:
    conn.execute(
        "INSERT INTO opportunities (item_id, name, category, score, est_margin,"
        " demand_note, next_action, raw_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            item_id, opp["name"], opp.get("category"), opp["score"],
            opp.get("est_margin"), opp.get("demand_note"), opp.get("next_action"),
            json.dumps(opp, ensure_ascii=False), _now(),
        ),
    )
    conn.commit()


def pending_notifications(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT o.*, i.url, i.source FROM opportunities o"
        " JOIN items i ON i.id = o.item_id WHERE o.notified = 0 ORDER BY o.score DESC"
    ).fetchall()


def mark_notified(conn: sqlite3.Connection, opp_ids: list[int]) -> None:
    conn.executemany("UPDATE opportunities SET notified = 1 WHERE id = ?", [(i,) for i in opp_ids])
    conn.commit()


def unpublished_opportunities(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT o.*, i.url, i.source, i.title AS item_title FROM opportunities o"
        " JOIN items i ON i.id = o.item_id WHERE o.published = 0 ORDER BY o.score DESC"
    ).fetchall()


def mark_published(conn: sqlite3.Connection, opp_ids: list[int]) -> None:
    conn.executemany("UPDATE opportunities SET published = 1 WHERE id = ?", [(i,) for i in opp_ids])
    conn.commit()
