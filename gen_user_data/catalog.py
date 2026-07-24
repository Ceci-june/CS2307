"""Xây dựng catalog listing (`listings.json`) từ listing_id THẬT.

Recommender thật lưu thuộc tính trong Postgres; ở môi trường cold-start này ta
chỉ có sẵn `backend/src/data/embeddings.pkl` (3037 listing_id thật + vector 768d).
Module này lấy các listing_id thật đó rồi mô phỏng thuộc tính (giá, diện tích,
quận, tiện ích) một cách nhất quán và có seed, để:

  * users/interactions tham chiếu tới listing có thật,
  * KG có node Listing với thuộc tính đầy đủ,
  * evaluation có ground-truth ổn định giữa các lần chạy.

Nếu sau này có dump thuộc tính thật (CSV/JSON), chỉ cần thay hàm
`load_listing_ids` / bổ sung `enrich_from_real_dump` là dữ liệu thật thay thế
phần mô phỏng — phần còn lại của pipeline không đổi.
"""
from __future__ import annotations

import json
import os
from typing import List

import numpy as np

from config import distribution_config as C
from schemas import (
    ACCESSIBILITY_FIELDS,
    AMENITY_FIELDS,
    VIEW_FIELDS,
    Listing,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
EMBEDDINGS_PKL = os.path.join(REPO_ROOT, "backend", "src", "data", "embeddings.pkl")
DATA_DIR = os.path.join(HERE, "data")
LISTINGS_PATH = os.path.join(DATA_DIR, "listings.json")

# Xác suất một feature = True, phụ thuộc phân khúc (luxury nhiều tiện ích hơn).
_FEATURE_BASE_P = {
    "affordable": 0.18,
    "mid_range": 0.35,
    "luxury": 0.62,
}


def load_listing_ids(limit: int | None = None) -> List[int]:
    """Đọc listing_id thật từ embeddings.pkl."""
    import pandas as pd  # local import: chỉ cần khi build catalog

    if not os.path.exists(EMBEDDINGS_PKL):
        raise FileNotFoundError(
            f"Không tìm thấy embeddings.pkl tại {EMBEDDINGS_PKL}. "
            "Đây là nguồn listing_id thật cho catalog."
        )
    df = pd.read_pickle(EMBEDDINGS_PKL)
    ids = [int(x) for x in df["listing_id"].tolist()]
    if limit:
        ids = ids[:limit]
    return ids


def _pick(rng: np.random.Generator, choices, weights) -> str:
    return str(rng.choice(choices, p=np.asarray(weights) / np.sum(weights)))


def build_catalog(seed: int = C.RANDOM_SEED, limit: int | None = None) -> List[Listing]:
    ids = load_listing_ids(limit=limit)
    rng = np.random.default_rng(seed)

    seg_names = list(C.BUDGET_SEGMENTS)
    seg_weights = np.array([C.BUDGET_SEGMENTS[s]["weight"] for s in seg_names])
    seg_weights = seg_weights / seg_weights.sum()

    listings: List[Listing] = []
    for lid in ids:
        segment = str(rng.choice(seg_names, p=seg_weights))
        lo, hi = C.BUDGET_SEGMENTS[segment]["price_range"]
        price = round(float(rng.uniform(lo, hi)), 2)

        ptype = _pick(rng, C.PROPERTY_TYPES, C.PROPERTY_TYPE_WEIGHTS)
        district = _pick(rng, C.DISTRICTS, C.DISTRICT_WEIGHTS)

        # Diện tích tương quan (thô) với giá.
        area = round(float(rng.normal(35 + price * 12, 15)), 1)
        area = max(20.0, area)
        bedrooms = int(np.clip(round(rng.normal(1 + price * 0.5, 1)), 0, 6))
        bathrooms = int(np.clip(round(bedrooms * 0.7 + rng.normal(0, 0.5)), 1, 5))

        p_feat = _FEATURE_BASE_P[segment]
        features = {}
        for f in AMENITY_FIELDS + ACCESSIBILITY_FIELDS + VIEW_FIELDS:
            features[f] = bool(rng.random() < p_feat)

        listings.append(
            Listing(
                listing_id=lid,
                title=f"{ptype} {bedrooms}PN tại {district}",
                property_type=ptype,
                district=district,
                price_billion=price,
                area_sqm=area,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                budget_group=segment,
                features=features,
            )
        )
    return listings


def save_catalog(listings: List[Listing], path: str = LISTINGS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([l.model_dump() for l in listings], f, ensure_ascii=False, indent=2)


def load_catalog(path: str = LISTINGS_PATH) -> List[Listing]:
    with open(path, encoding="utf-8") as f:
        return [Listing(**row) for row in json.load(f)]


if __name__ == "__main__":
    cat = build_catalog()
    save_catalog(cat)
    seg_counts = {}
    for l in cat:
        seg_counts[l.budget_group] = seg_counts.get(l.budget_group, 0) + 1
    print(f"[catalog] {len(cat)} listings -> {LISTINGS_PATH}")
    print("[catalog] budget segment distribution:",
          {k: round(v / len(cat), 3) for k, v in sorted(seg_counts.items())})
