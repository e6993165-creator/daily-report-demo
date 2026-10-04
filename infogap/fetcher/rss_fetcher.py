"""RSS / Atom 採集器。

禮貌抓取:帶 ETag / Last-Modified 條件請求,304 時回空清單,
不對來源站重複拉全文。
"""

from __future__ import annotations

import feedparser

from .base import BaseFetcher

# 行程內的 ETag 快取;跨行程的話可改存 DB(骨架先求簡單)
_etag_cache: dict[str, tuple[str | None, str | None]] = {}


class RssFetcher(BaseFetcher):
    def fetch(self) -> list[dict]:
        etag, modified = _etag_cache.get(self.url, (None, None))
        parsed = feedparser.parse(
            self.url,
            etag=etag,
            modified=modified,
            request_headers={"User-Agent": self.session.headers["User-Agent"]},
        )
        if getattr(parsed, "status", None) == 304:
            return []
        if parsed.bozo and not parsed.entries:
            # 解析失敗且拿不到任何項目 → 當作來源故障,往上拋
            raise RuntimeError(f"RSS 解析失敗: {parsed.bozo_exception!r}")

        _etag_cache[self.url] = (
            getattr(parsed, "etag", None),
            getattr(parsed, "modified", None),
        )

        items = []
        for e in parsed.entries:
            link = getattr(e, "link", None)
            title = getattr(e, "title", None)
            if not link or not title:
                continue
            items.append({
                "source": self.name,
                "title": title,
                "url": link,
                "summary": getattr(e, "summary", None),
                "published_at": getattr(e, "published", None),
            })
        return items
