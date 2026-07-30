from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger


SYSTEM_PROMPT = """Bạn là trợ lý tư vấn bất động sản Việt Nam.
Chỉ sử dụng dữ liệu ứng viên và evidence được cung cấp; không bổ sung hoặc suy diễn dữ kiện.
Trả về đúng một JSON object, không markdown, theo cấu trúc:
{
  "answer": "Lời trả lời ngắn gọn bằng tiếng Việt, tóm tắt kết quả phù hợp với yêu cầu",
  "properties": [
    {
      "listing_id": "ID giữ nguyên như đầu vào",
      "explanation": "Lý do căn này phù hợp dựa trên dữ liệu/evidence",
      "comparison": "Điểm mạnh hoặc đánh đổi của căn này so với các căn còn lại"
    }
  ]
}
Phải trả đủ một phần tử properties cho mỗi ứng viên. Nếu dữ liệu không đủ để so sánh,
nói rõ điều đó thay vì tự bịa. Không đưa thông tin liên hệ hay lời chào vào answer.
"""


def _compact_candidate(item: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "listing_id",
        "property_type",
        "title",
        "address",
        "district",
        "price_range",
        "area",
        "bedrooms",
        "bathrooms",
        "legal_status",
        "furnishing",
        "final_score",
        "score_breakdown",
        "matched_criteria",
        "evidence",
    )
    candidate = {key: item.get(key) for key in fields if item.get(key) is not None}
    description = str(item.get("description") or "").strip()
    if description:
        candidate["description_excerpt"] = description[:800]
    return candidate


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```")
        text = text.removesuffix("```").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM search answer must be a JSON object")
    return parsed


class LLMSearchAnswerGenerator:
    def __init__(self, llm_model):
        self.llm_model = llm_model

    @staticmethod
    def enabled() -> bool:
        return os.getenv("SEARCH_USE_LLM_ANSWER", "false").lower() in {"1", "true", "yes"}

    async def generate(
        self,
        query: str,
        parsed_query: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> tuple[str | None, bool]:
        if not self.enabled() or not results:
            return None, False

        candidates = [_compact_candidate(item) for item in results]
        user_prompt = json.dumps(
            {
                "user_query": query,
                "parsed_query": parsed_query,
                "candidates": candidates,
            },
            ensure_ascii=False,
            default=str,
        )
        ok, raw, error = await self.llm_model.ask_llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        if not ok or not raw:
            logger.warning("LLM search answer unavailable: {}", error)
            return None, False

        try:
            payload = _parse_json_object(raw)
            answer = payload.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("LLM search answer is empty")

            by_listing_id = {
                str(item.get("listing_id")): item
                for item in payload.get("properties", [])
                if isinstance(item, dict) and item.get("listing_id") is not None
            }
            for result in results:
                insight = by_listing_id.get(str(result.get("listing_id")))
                if not insight:
                    continue
                explanation = insight.get("explanation")
                comparison = insight.get("comparison")
                if isinstance(explanation, str) and explanation.strip():
                    result["explanation"] = explanation.strip()
                if isinstance(comparison, str) and comparison.strip():
                    result["comparison"] = comparison.strip()
            return answer.strip(), True
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Invalid LLM search answer; using deterministic fallback: {}", exc)
            return None, False
