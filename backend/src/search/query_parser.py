from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from src.search.normalizer import (
    AMENITY_CATEGORY_ALIASES,
    FEATURE_ALIASES,
    PROPERTY_TYPE_ALIASES,
    csv_values,
    first_alias_match,
    normalize_text,
    price_to_billion,
)
from src.search.schemas import (
    AmenityDistanceFilter,
    HardFilters,
    ParsedSearchQuery,
    RankingProfile,
    SoftPreference,
)


MUST_WORDS = ("bat buoc", "phai co", "chi lay", "khong vuot qua", "khong qua")


class RuleBasedQueryParser:
    """Deterministic Vietnamese parser. LLM output may enrich, never bypass, this schema."""

    def parse(self, query: str, top_k: int = 20, explicit_filters: Optional[Dict[str, Any]] = None) -> ParsedSearchQuery:
        normalized = normalize_text(query)
        hard = HardFilters()
        protected = [word for word in MUST_WORDS if word in normalized]

        self._parse_price(normalized, hard)
        self._parse_area(normalized, hard)
        self._parse_rooms(normalized, hard)
        self._parse_property_types(normalized, hard)
        self._parse_locations(query, normalized, hard)
        self._parse_legal_furnishing(normalized, hard)

        required_features = []
        soft_preferences = []
        for feature in first_alias_match(query, FEATURE_ALIASES):
            aliases = FEATURE_ALIASES[feature]
            is_required = any(f"{must} {alias}" in normalized for must in MUST_WORDS for alias in aliases)
            if is_required:
                required_features.append(feature)
            else:
                soft_preferences.append(SoftPreference(type="feature", value=feature, weight=0.7))
        hard.required_features = sorted(set(required_features))

        amenity_filters = self._parse_amenity_distances(normalized)
        profile = self._ranking_profile(normalized)
        parsed = ParsedSearchQuery(
            hard_filters=hard,
            amenity_filters=amenity_filters,
            soft_preferences=soft_preferences,
            semantic_query=query.strip(),
            negative_preferences=self._negative_phrases(query),
            ranking_profile=profile,
            top_k=top_k,
            protected_constraints=protected,
        )
        self.apply_explicit_filters(parsed, explicit_filters or {})
        return parsed

    @staticmethod
    def _parse_price(text: str, hard: HardFilters) -> None:
        patterns = (
            ("max", r"(?:duoi|toi da|khong qua|khong vuot qua)\s*(\d+(?:[.,]\d+)?)\s*(ty|trieu)"),
            ("min", r"(?:tren|toi thieu|tu)\s*(\d+(?:[.,]\d+)?)\s*(ty|trieu)"),
            ("target", r"(?:khoang|tam)\s*(\d+(?:[.,]\d+)?)\s*(ty|trieu)"),
        )
        for field, pattern in patterns:
            match = re.search(pattern, text)
            if match:
                setattr(hard.price, field, price_to_billion(float(match.group(1).replace(",", ".")), match.group(2)))

    @staticmethod
    def _parse_area(text: str, hard: HardFilters) -> None:
        patterns = (
            ("max", r"(?:dien tich\s*)?(?:duoi|toi da|khong qua)\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong)"),
            ("min", r"(?:dien tich\s*)?(?:tren|toi thieu|tu)\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong)"),
            ("target", r"(?:dien tich\s*)?(?:khoang|tam)\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong)"),
        )
        for field, pattern in patterns:
            match = re.search(pattern, text)
            if match:
                setattr(hard.area, field, float(match.group(1).replace(",", ".")))

    @staticmethod
    def _parse_rooms(text: str, hard: HardFilters) -> None:
        bed = re.search(r"(?:tu\s*)?(\d+)\s*(?:pn|phong ngu)", text)
        bath = re.search(r"(?:tu\s*)?(\d+)\s*(?:wc|phong tam|phong ve sinh)", text)
        if bed:
            hard.bedrooms.min = int(bed.group(1))
        if bath:
            hard.bathrooms.min = int(bath.group(1))

    @staticmethod
    def _parse_property_types(text: str, hard: HardFilters) -> None:
        for canonical, aliases in PROPERTY_TYPE_ALIASES.items():
            for alias in aliases:
                if re.search(rf"(?:khong lay|loai tru|khong chon)\s+{re.escape(alias)}", text):
                    hard.excluded_property_types.append(canonical)
                elif alias in text:
                    hard.property_types.append(canonical)
                    break

    @staticmethod
    def _parse_locations(original: str, text: str, hard: HardFilters) -> None:
        # Stop at punctuation or common constraint words to avoid swallowing the query.
        match = re.search(
            r"\b(thanh pho|thi xa|huyen|phuong|quan|xa|tp)\s+"
            r"([a-z0-9 ]{1,40}?)(?=\s*(?:,|;|\.|cu\b|duoi|tren|gan|tu\s+\d|\d+\s*(?:pn|phong)|$))",
            text,
        )
        if match:
            prefix = {
                "phuong": "Phường", "xa": "Xã", "quan": "Quận",
                "huyen": "Huyện", "thi xa": "Thị Xã",
                "thanh pho": "Thành Phố", "tp": "Thành Phố",
            }[match.group(1)]
            name = " ".join(part.capitalize() for part in match.group(2).strip().split())
            location = f"{prefix} {name}"
            # In the V2 graph, district-level units are former administrative
            # areas; current locations are represented by Phường/Xã wards.
            if prefix not in {"Phường", "Xã"}:
                hard.former_admin_areas.append(location)
            else:
                hard.districts.append(location)
        if "thu duc" in text and not hard.districts and not hard.former_admin_areas:
            # Dataset contains both the former city label and pre-2021 districts.
            hard.former_admin_areas.extend(["Thành Phố Thủ Đức", "Quận 2", "Quận 9", "Quận Thủ Đức"])

    @staticmethod
    def _parse_legal_furnishing(text: str, hard: HardFilters) -> None:
        if "so hong" in text or "so do" in text:
            hard.legal_statuses.append("Sổ hồng riêng")
        furnishing = {
            "day du noi that": "Đầy đủ",
            "full noi that": "Đầy đủ",
            "noi that cao cap": "Cao cấp",
            "noi that co ban": "Cơ bản",
            "khong noi that": "Không nội thất",
        }
        for phrase, value in furnishing.items():
            if phrase in text:
                hard.furnishings.append(value)

    @staticmethod
    def _parse_amenity_distances(text: str):
        results = []
        for category, aliases in AMENITY_CATEGORY_ALIASES.items():
            for alias in aliases:
                pattern = rf"(?:cach|gan)\s+{re.escape(alias)}(?:\s+khong)?\s*(?:qua|duoi|toi da|trong vong)?\s*(\d+(?:[.,]\d+)?)\s*(km|m|phut)"
                match = re.search(pattern, text)
                if not match:
                    continue
                value = float(match.group(1).replace(",", "."))
                unit = match.group(2)
                kwargs = {"amenity_category": category, "required": True}
                if unit == "phut":
                    kwargs["max_duration_min"] = value
                else:
                    kwargs["max_driving_distance_km"] = value / 1000 if unit == "m" else value
                results.append(AmenityDistanceFilter(**kwargs))
                break
        return results

    @staticmethod
    def _ranking_profile(text: str) -> RankingProfile:
        if "quan trong nhat" in text and any(x in text for x in ("metro", "vi tri", "di lam")):
            return RankingProfile.LOCATION_FIRST
        if "gia dinh" in text or "tre em" in text:
            return RankingProfile.FAMILY
        if "dau tu" in text or "sinh loi" in text:
            return RankingProfile.INVESTMENT
        if "gia re" in text or "uu tien gia" in text:
            return RankingProfile.PRICE_FIRST
        return RankingProfile.BALANCED

    @staticmethod
    def _negative_phrases(query: str):
        # Comparative constraints such as "không quá 3 km" are limits, not
        # negative preferences.
        return [
            match.group(1).strip()
            for match in re.finditer(r"(?:tránh|không\s+(?!quá\b|vượt\b))([^,;.]+)", query.lower())
        ]

    @staticmethod
    def apply_explicit_filters(parsed: ParsedSearchQuery, filters: Dict[str, Any]) -> None:
        hard = parsed.hard_filters
        mapping = {
            "min_price": (hard.price, "min", float), "max_price": (hard.price, "max", float),
            "min_area": (hard.area, "min", float), "max_area": (hard.area, "max", float),
            "bedrooms": (hard.bedrooms, "min", int), "bathrooms": (hard.bathrooms, "min", int),
        }
        for key, (target, field, caster) in mapping.items():
            value = filters.get(key)
            if value not in (None, "", 0, "0"):
                setattr(target, field, caster(value))
        list_mapping = {
            "district": "districts", "property_type": "property_types",
            "legal_status": "legal_statuses", "furniture": "furnishings",
            "house_direction": "house_directions", "balcony_direction": "balcony_directions",
        }
        for source, target in list_mapping.items():
            values = csv_values(filters.get(source))
            if values:
                setattr(hard, target, values)
        for feature in FEATURE_ALIASES:
            if filters.get(feature) is True:
                hard.required_features.append(feature)
        hard.required_features = sorted(set(hard.required_features))


class LLMQueryParser:
    """Optional schema-constrained enrichment. Disabled by default for deterministic serving."""

    def __init__(self, llm_model):
        self.llm_model = llm_model

    async def parse(self, query: str, fallback: ParsedSearchQuery) -> ParsedSearchQuery:
        if os.getenv("SEARCH_USE_LLM_PARSER", "false").lower() not in {"1", "true", "yes"}:
            return fallback
        prompt = (
            "Parse the Vietnamese real-estate query into JSON matching this schema. "
            "Do not generate SQL. Preserve hard constraints. JSON only.\nSchema:\n"
            + json.dumps(ParsedSearchQuery.model_json_schema(), ensure_ascii=False)
            + "\nQuery:\n" + query
        )
        ok, raw, _ = await self.llm_model.ask_llm(
            system_prompt="You are a strict query parser. Return valid JSON only.",
            user_prompt=prompt,
        )
        if not ok or not raw:
            return fallback
        try:
            parsed = ParsedSearchQuery.model_validate_json(raw.strip().removeprefix("```json").removesuffix("```").strip())
            # Deterministic constraints win over LLM output.
            parsed.hard_filters = fallback.hard_filters
            parsed.amenity_filters = fallback.amenity_filters
            parsed.protected_constraints = fallback.protected_constraints
            return parsed
        except Exception:
            return fallback
