"""Sinh câu truy vấn ngôn ngữ tự nhiên (`raw_query`) cho interaction.

`raw_query` là chỗ LLM tạo giá trị thật (ngôn ngữ đời thường, có nhiễu) — nên
đây là điểm tích hợp LLM. Tuy nhiên pipeline phải chạy được OFFLINE và tất định:

  * Mặc định: template-based generator (không cần mạng, có seed) -> tái lập được.
  * Tuỳ chọn: nếu đặt USE_LLM=1 và có API key, có thể nối vào
    backend/src/services/llm. Phần distribution (giá, intent, action...) KHÔNG
    giao cho LLM vì LLM hay trôi về trung bình — ta kiểm soát bằng RNG có seed.

Thiết kế theo interface để dễ thay backend LLM sau này.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import numpy as np

# Mẫu câu theo intent -> danh sách template. {district}, {price}, {beds} được điền.
_TEMPLATES: Dict[str, list] = {
    "buy_for_living": [
        "{ptype} {district} cho gia đình giá khoảng {price} tỷ",
        "cần mua {ptype} {beds} phòng ngủ ở {district} để ở",
        "tìm {ptype} {district} gần trường học tầm {price} tỷ",
        "{ptype} {district} rẻ một chút cho vợ chồng mới cưới",
        "nhà ở {district} thoáng mát, {beds}pn, dưới {price} tỷ",
    ],
    "investment": [
        "{ptype} {district} cho thuê lại được giá tốt",
        "tìm {ptype} {district} tiềm năng tăng giá tầm {price} tỷ",
        "mua {ptype} đầu tư ở {district} pháp lý rõ ràng",
        "{ptype} {district} dòng tiền tốt khoảng {price} tỷ",
    ],
    "rent": [
        "thuê {ptype} {district} {beds} phòng ngủ",
        "cần thuê {ptype} {district} full nội thất giá rẻ",
        "{ptype} {district} cho thuê gần metro",
        "tìm phòng {ptype} ở {district} tầm {price} triệu/tháng",
    ],
}


class QueryGenerator:
    """Sinh raw_query. Offline template hoặc (tuỳ chọn) LLM thật."""

    def __init__(self, seed: int, use_llm: Optional[bool] = None):
        self.rng = np.random.default_rng(seed)
        if use_llm is None:
            use_llm = os.getenv("USE_LLM", "0") == "1"
        self.use_llm = use_llm
        self._llm = self._maybe_init_llm() if use_llm else None

    def _maybe_init_llm(self):
        try:
            # Điểm nối LLM thật: tái sử dụng service backend nếu chạy được.
            from src.services.llm.llm_model import LLMModel  # type: ignore

            return LLMModel()
        except Exception as e:  # pragma: no cover - phụ thuộc môi trường
            print(f"[llm_client] Không init được LLM ({e}); fallback template.")
            self.use_llm = False
            return None

    def generate(self, *, intent: str, district: str, price: float,
                 beds: int, property_type: str) -> str:
        if self.use_llm and self._llm is not None:  # pragma: no cover
            return self._generate_llm(intent, district, price, beds, property_type)
        return self._generate_template(intent, district, price, beds, property_type)

    def _generate_template(self, intent, district, price, beds, ptype) -> str:
        templates = _TEMPLATES.get(intent, _TEMPLATES["buy_for_living"])
        t = str(self.rng.choice(templates))
        price_str = f"{price:.1f}".rstrip("0").rstrip(".")
        return t.format(district=district, price=price_str, beds=beds,
                        ptype=ptype.lower())

    def _generate_llm(self, intent, district, price, beds, ptype) -> str:  # pragma: no cover
        prompt = (
            "Viết MỘT câu tìm kiếm bất động sản bằng tiếng Việt, giọng đời thường, "
            f"ý định={intent}, khu vực={district}, loại={ptype}, "
            f"~{beds} phòng ngủ, ngân sách ~{price} tỷ. Chỉ trả về câu, không giải thích."
        )
        try:
            return self._llm.generate(prompt).strip()  # type: ignore[attr-defined]
        except Exception:
            return self._generate_template(intent, district, price, beds, ptype)
