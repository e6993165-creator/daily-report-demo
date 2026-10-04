"""模組二:AI 價值分析引擎(串接 Claude API)。

- structured outputs(json_schema)保證回傳可解析;Pydantic 在客戶端再驗一次。
- 已啟用 server-side fallback:安全分類器拒答時由 API 端自動換模型重跑,
  整條鏈都拒答才會收到 stop_reason == "refusal"(該批略過並記 log,不矇混)。
- API 金鑰走 ANTHROPIC_API_KEY 環境變數,SDK 自動讀取。
"""

from __future__ import annotations

import json
import logging

import anthropic
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
你是跨境資訊差分析師。你會收到一批來自公開 RSS / 論壇 API 的資訊項目。
任務:找出「台灣人通常不知道、國外很便宜、或台灣極度缺乏」的特定商品、服務或數位資產,
並估算潛在價差與需求熱度。

規則:
- 只回報有具體落點的項目;泛泛的新聞、與套利無關的內容一律不收。
- score 為 0-100 的潛力分數,估算依據寫進 demand_note。
- est_margin 是文字描述(例如「美國定價 $29,台灣代購行情 NT$1800,毛利約 40%」),
  沒有把握的數字寧可寫區間或寫「無法估算」,不要編造精確值。
- next_action 給一個可立刻執行的查證或行動步驟。
"""


class Opportunity(BaseModel):
    item_index: int = Field(description="對應輸入清單的 index(從 0 起算)")
    name: str = Field(description="商品/服務/數位資產名稱")
    category: str = Field(description="類別,如 實體商品/數位服務/訂閱帳號/資訊產品")
    score: int = Field(ge=0, le=100, description="潛力分數")
    est_margin: str = Field(description="潛在價差/利潤空間的文字估算")
    demand_note: str = Field(description="需求熱度判斷與依據")
    next_action: str = Field(description="建議的下一步行動")


class AnalysisResult(BaseModel):
    opportunities: list[Opportunity]


_OUTPUT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "opportunities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_index": {"type": "integer"},
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "score": {"type": "integer"},
                        "est_margin": {"type": "string"},
                        "demand_note": {"type": "string"},
                        "next_action": {"type": "string"},
                    },
                    "required": [
                        "item_index", "name", "category", "score",
                        "est_margin", "demand_note", "next_action",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["opportunities"],
        "additionalProperties": False,
    },
}


def analyze_batch(
    items: list[dict],
    model: str = "claude-opus-5-5",
    min_score: int = 60,
) -> list[Opportunity]:
    """把一批 items 丟給 Claude,回傳通過 min_score 門檻的機會清單。

    items 每筆至少要有 title / url / summary / source 欄位。
    """
    if not items:
        return []

    client = anthropic.Anthropic()

    payload = [
        {
            "index": i,
            "source": it["source"],
            "title": it["title"],
            "url": it["url"],
            "summary": (it.get("summary") or "")[:1500],
        }
        for i, it in enumerate(items)
    ]

    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        output_config={"format": _OUTPUT_SCHEMA},
        messages=[{
            "role": "user",
            "content": "待分析項目如下(JSON):\n"
                       + json.dumps(payload, ensure_ascii=False, indent=1),
        }],
    )

    if response.stop_reason == "refusal":
        detail = getattr(response, "stop_details", None)
        logger.warning("Claude 拒答,本批 %d 筆略過。stop_details=%r", len(items), detail)
        return []
    if response.stop_reason == "max_tokens":
        logger.warning("輸出被 max_tokens 截斷,本批結果不可信,略過(可調小 batch_size)")
        return []

    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        result = AnalysisResult.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.error("結構化輸出驗證失敗: %s;原文前 500 字: %.500s", exc, text)
        return []

    kept = [o for o in result.opportunities if o.score >= min_score]
    logger.info(
        "分析 %d 筆 → 模型回報 %d 個機會 → 過 min_score=%d 門檻 %d 個",
        len(items), len(result.opportunities), min_score, len(kept),
    )
    return kept
