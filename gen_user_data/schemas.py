"""Pydantic schema cho dữ liệu mô phỏng: Listing, User, Interaction.

Dùng để validate mọi JSON sinh ra (fail sớm nếu generator tạo dữ liệu sai),
và là "hợp đồng" thống nhất giữa các bước generation -> KG -> evaluation.

Field amenity/accessibility/view khớp chính xác tên trong
backend/src/services/inference/knowledge.py để KG map thẳng sang listing thật.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator

# Tên field boolean hợp lệ (đồng bộ với knowledge.py)
AMENITY_FIELDS = [
    "balcony", "garden", "garage", "terrace", "pool", "gym", "park", "bbq",
    "kids_playground", "sports_court", "security_24h", "reception",
    "elevator", "parking",
]
ACCESSIBILITY_FIELDS = [
    "near_metro", "near_bus", "near_highway", "near_school",
    "near_hospital", "near_mall", "near_market", "near_park",
]
VIEW_FIELDS = ["river_view", "park_view", "city_view"]
BOOLEAN_FEATURE_FIELDS = AMENITY_FIELDS + ACCESSIBILITY_FIELDS + VIEW_FIELDS

ACTION_TYPES = ["view", "save", "share", "contact"]
SOURCES = ["search_bar", "ai_recommendation", "homepage", "related_items"]
INTENTS = ["buy_for_living", "investment", "rent"]
BUDGET_GROUPS = ["affordable", "mid_range", "luxury"]


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
class Listing(BaseModel):
    """Catalog item. listing_id là ID THẬT lấy từ embeddings.pkl; các thuộc
    tính còn lại được mô phỏng nhất quán để phục vụ KG + evaluation."""

    listing_id: int
    title: str
    property_type: str
    district: str
    price_billion: float = Field(..., ge=0)
    area_sqm: float = Field(..., gt=0)
    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=0)
    budget_group: str
    features: Dict[str, bool] = Field(default_factory=dict)

    @field_validator("features")
    @classmethod
    def _known_features(cls, v: Dict[str, bool]) -> Dict[str, bool]:
        unknown = set(v) - set(BOOLEAN_FEATURE_FIELDS)
        if unknown:
            raise ValueError(f"Feature không hợp lệ: {sorted(unknown)}")
        return v


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class Demographics(BaseModel):
    age_group: str
    marital_status: str
    has_children: bool
    income_level: str


class ExplicitPreferences(BaseModel):
    preferred_districts: List[str]
    min_bedrooms: int = Field(..., ge=0)
    budget_range: Tuple[float, float]  # (min, max) tỷ VNĐ
    property_type: List[str]
    liked_amenities: List[str] = Field(default_factory=list)

    @field_validator("liked_amenities")
    @classmethod
    def _known_amenities(cls, v: List[str]) -> List[str]:
        unknown = set(v) - set(BOOLEAN_FEATURE_FIELDS)
        if unknown:
            raise ValueError(f"Amenity không hợp lệ: {sorted(unknown)}")
        return v

    @field_validator("budget_range")
    @classmethod
    def _valid_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        lo, hi = v
        if lo < 0 or hi < lo:
            raise ValueError(f"budget_range không hợp lệ: {v}")
        return v


class UserProfile(BaseModel):
    user_id: str
    segment: str  # affordable | mid_range | luxury (phân khúc chủ đạo)
    primary_intent: str
    demographics: Demographics
    explicit_preferences: ExplicitPreferences


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------
class SearchContext(BaseModel):
    raw_query: str
    filters_applied: Dict[str, float] = Field(default_factory=dict)
    inferred_intent: str
    budget_group: str


class Interaction(BaseModel):
    interaction_id: str
    user_id: str
    session_id: str
    listing_id: int
    action_type: str
    timestamp: str  # ISO-8601 UTC
    dwell_time_seconds: int = Field(..., ge=0)
    source: str
    context: SearchContext
    implicit_score: float = Field(..., ge=0)
    is_bounce: bool = False

    @field_validator("action_type")
    @classmethod
    def _valid_action(cls, v: str) -> str:
        if v not in ACTION_TYPES:
            raise ValueError(f"action_type không hợp lệ: {v}")
        return v

    @field_validator("source")
    @classmethod
    def _valid_source(cls, v: str) -> str:
        if v not in SOURCES:
            raise ValueError(f"source không hợp lệ: {v}")
        return v
