"""模組四:內容自動生成與發布(Auto-Publisher)。

產出兩份 Markdown 檔:
  content/YYYY-MM-DD-digest-free.md   免費版懶人包(引流用)
  content/YYYY-MM-DD-digest-paid.md   付費版深度分析(訂閱制平台用)

部署邊界(重要):Substack 與方格子都沒有公開的「發文 API」,
這一段自動化止於「產出成稿檔案」;上架動作目前只能人工貼上,
或自行接 Substack 的 email-to-post 等非官方流程。檔案生成 ≠ 已發布。
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

FREE_PROMPT = """\
用以下高價值資訊差項目,寫一篇繁體中文「免費版懶人包」Markdown 文章:
- 目標:社群/部落格引流,語氣輕快、重點條列。
- 每個項目只給方向與來源連結,保留細節(具體利潤估算、操作步驟)不寫,
  文末導流一句「完整分析在付費版」。
- 不捏造數字;來源只用提供的 URL。
"""

PAID_PROMPT = """\
用以下高價值資訊差項目,寫一篇繁體中文「付費版深度分析」Markdown 文章:
- 每個項目含:機會描述、價差/利潤估算(引用提供的 est_margin,不自行加碼)、
  需求熱度依據、具體執行步驟、風險(匯率、關稅、平台規則、合法性)。
- 數字沒有依據就寫區間或明講無法估算,不得編造。
"""


def _generate(client: anthropic.Anthropic, model: str, prompt: str, opps: list[dict]) -> str:
    payload = json.dumps(opps, ensure_ascii=False, indent=1)
    with client.beta.messages.stream(
        model=model,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt + "\n\n項目資料(JSON):\n" + payload}],
    ) as stream:
        response = stream.get_final_message()
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude 拒答,stop_details={getattr(response, 'stop_details', None)!r}")
    return "".join(b.text for b in response.content if b.type == "text")


def publish_pending(
    opportunities: list[dict],
    output_dir: str | Path = "content",
    model: str = "claude-opus-5-5",
) -> tuple[Path, Path] | None:
    """把未發布的機會寫成免費/付費兩版成稿。回傳 (free_path, paid_path)。

    opportunities 為 DB rows 轉成的 dict 清單;空清單時回 None 並記 log。
    """
    if not opportunities:
        logger.info("沒有待發布項目,本輪不產稿")
        return None

    client = anthropic.Anthropic()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    slim = [
        {k: o.get(k) for k in
         ("name", "category", "score", "est_margin", "demand_note", "next_action", "url", "source")}
        for o in opportunities
    ]

    free_md = _generate(client, model, FREE_PROMPT, slim)
    paid_md = _generate(client, model, PAID_PROMPT, slim)

    free_path = out / f"{today}-digest-free.md"
    paid_path = out / f"{today}-digest-paid.md"
    free_path.write_text(free_md, encoding="utf-8")
    paid_path.write_text(paid_md, encoding="utf-8")
    logger.info("成稿輸出:%s(%d 字)、%s(%d 字)",
                free_path, len(free_md), paid_path, len(paid_md))
    return free_path, paid_path
