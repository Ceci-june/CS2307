from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NumericRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    target: Optional[float] = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must be less than or equal to max")
        return self


class IntegerRange(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    target: Optional[int] = None


class AmenityDistanceFilter(BaseModel):
    amenity_category: str
    max_driving_distance_km: Optional[float] = None
    max_duration_min: Optional[float] = None
    required: bool = True


class SoftPreference(BaseModel):
    type: str
    value: Optional[str] = None
    amenity_category: Optional[str] = None
    weight: float = Field(default=0.5, ge=0, le=1)


class RankingProfile(str, Enum):
    BALANCED = "BALANCED"
    LOCATION_FIRST = "LOCATION_FIRST"
    AMENITY_FIRST = "AMENITY_FIRST"
    PRICE_FIRST = "PRICE_FIRST"
    SEMANTIC_FIRST = "SEMANTIC_FIRST"
    INVESTMENT = "INVESTMENT"
    FAMILY = "FAMILY"


class HardFilters(BaseModel):
    price: NumericRange = Field(default_factory=NumericRange)
    area: NumericRange = Field(default_factory=NumericRange)
    bedrooms: IntegerRange = Field(default_factory=IntegerRange)
    bathrooms: IntegerRange = Field(default_factory=IntegerRange)
    property_types: List[str] = Field(default_factory=list)
    excluded_property_types: List[str] = Field(default_factory=list)
    districts: List[str] = Field(default_factory=list)
    former_admin_areas: List[str] = Field(default_factory=list)
    legal_statuses: List[str] = Field(default_factory=list)
    furnishings: List[str] = Field(default_factory=list)
    house_directions: List[str] = Field(default_factory=list)
    balcony_directions: List[str] = Field(default_factory=list)
    required_features: List[str] = Field(default_factory=list)
    excluded_features: List[str] = Field(default_factory=list)


class ParsedSearchQuery(BaseModel):
    intent: str = "property_search"
    hard_filters: HardFilters = Field(default_factory=HardFilters)
    amenity_filters: List[AmenityDistanceFilter] = Field(default_factory=list)
    soft_preferences: List[SoftPreference] = Field(default_factory=list)
    semantic_query: str = ""
    negative_preferences: List[str] = Field(default_factory=list)
    ranking_profile: RankingProfile = RankingProfile.BALANCED
    sort: str = "relevance"
    top_k: int = Field(default=20, ge=1, le=100)
    protected_constraints: List[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)
    debug: bool = False
    filters: Dict[str, Any] = Field(default_factory=dict)


class ParseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=20, ge=1, le=100)


class SimilarRequest(BaseModel):
    top_k: int = Field(default=10, ge=1, le=50)

