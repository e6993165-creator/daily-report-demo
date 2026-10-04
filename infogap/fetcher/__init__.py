"""模組一:自動化資訊採集器(Auto-Fetcher)。

可擴展架構:每種來源型別是一個 BaseFetcher 子類,
在 FETCHER_TYPES 註冊後即可由 config.yaml 的 sources[].type 指定。
"""

from __future__ import annotations

import logging

from .base import BaseFetcher
from .rss_fetcher import RssFetcher
from .api_fetcher import JsonApiFetcher

logger = logging.getLogger(__name__)

FETCHER_TYPES: dict[str, type[BaseFetcher]] = {
    "rss": RssFetcher,
    "json_api": JsonApiFetcher,
}


def run_all(sources: list[dict], fetch_cfg: dict) -> tuple[list[dict], list[str]]:
    """跑完所有來源。回傳 (items, failures) — 單一來源失敗不中斷其他來源,
    但失敗清單一路帶回給呼叫端,不默默吞掉。"""
    all_items: list[dict] = []
    failures: list[str] = []
    for src in sources:
        cls = FETCHER_TYPES.get(src.get("type", ""))
        if cls is None:
            failures.append(f"{src.get('name', '?')}: 未知的來源型別 {src.get('type')!r}")
            continue
        try:
            items = cls(src, fetch_cfg).fetch()
            logger.info("來源 %s 抓到 %d 筆", src["name"], len(items))
            all_items.extend(items)
        except Exception as exc:  # noqa: BLE001 — 失效要出聲但不癱瘓整輪
            failures.append(f"{src['name']}: {type(exc).__name__}: {exc}")
    return all_items, failures
