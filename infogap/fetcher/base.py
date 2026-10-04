from __future__ import annotations

from abc import ABC, abstractmethod

import requests


class BaseFetcher(ABC):
    """所有採集器的基底。子類只需實作 fetch(),回傳標準化 dict 清單:

    {"source": str, "title": str, "url": str,
     "summary": str | None, "published_at": str | None}
    """

    def __init__(self, source_cfg: dict, fetch_cfg: dict):
        self.cfg = source_cfg
        self.name: str = source_cfg["name"]
        self.url: str = source_cfg["url"]
        self.timeout: int = fetch_cfg.get("timeout_seconds", 20)
        self.session = requests.Session()
        self.session.headers["User-Agent"] = fetch_cfg.get(
            "user_agent", "infogap-monitor/0.1"
        )

    @abstractmethod
    def fetch(self) -> list[dict]: ...
