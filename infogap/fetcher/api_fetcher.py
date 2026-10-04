"""公開 JSON API 採集器。

不同 API 的回應結構不同,各自寫一支解析函式註冊進 PARSERS,
config.yaml 的 sources[].parser 指定用哪支。新增來源 = 新增一支函式。
"""

from __future__ import annotations

from typing import Callable

from .base import BaseFetcher

Parser = Callable[[dict, str], list[dict]]


def parse_reddit_listing(data: dict, source_name: str) -> list[dict]:
    """Reddit 的 /xxx/new.json 公開列表格式。"""
    items = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        if not d.get("permalink") or not d.get("title"):
            continue
        items.append({
            "source": source_name,
            "title": d["title"],
            "url": "https://www.reddit.com" + d["permalink"],
            "summary": (d.get("selftext") or "")[:2000] or None,
            "published_at": str(d.get("created_utc")),
        })
    return items


def parse_hn_algolia(data: dict, source_name: str) -> list[dict]:
    """Hacker News Algolia 搜尋 API(https://hn.algolia.com/api)。"""
    items = []
    for hit in data.get("hits", []):
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if not hit.get("title"):
            continue
        items.append({
            "source": source_name,
            "title": hit["title"],
            "url": url,
            "summary": hit.get("story_text"),
            "published_at": hit.get("created_at"),
        })
    return items


PARSERS: dict[str, Parser] = {
    "reddit_listing": parse_reddit_listing,
    "hn_algolia": parse_hn_algolia,
}


class JsonApiFetcher(BaseFetcher):
    def fetch(self) -> list[dict]:
        parser_name = self.cfg.get("parser")
        parser = PARSERS.get(parser_name or "")
        if parser is None:
            raise ValueError(
                f"來源 {self.name} 的 parser={parser_name!r} 未在 PARSERS 註冊"
            )
        resp = self.session.get(self.url, timeout=self.timeout)
        resp.raise_for_status()
        return parser(resp.json(), self.name)
