from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List

from src.search.schemas import ParsedSearchQuery, RankingProfile


WEIGHTS: Dict[RankingProfile, Dict[str, float]] = {
    RankingProfile.BALANCED: {"semantic": .45, "amenity": .15, "features": .10, "location": .10, "target": .08, "freshness": .07, "quality": .05},
    RankingProfile.LOCATION_FIRST: {"semantic": .25, "amenity": .30, "features": .08, "location": .20, "target": .07, "freshness": .05, "quality": .05},
    RankingProfile.AMENITY_FIRST: {"semantic": .25, "amenity": .40, "features": .12, "location": .08, "target": .05, "freshness": .05, "quality": .05},
    RankingProfile.PRICE_FIRST: {"semantic": .25, "amenity": .10, "features": .08, "location": .08, "target": .30, "freshness": .10, "quality": .09},
    RankingProfile.SEMANTIC_FIRST: {"semantic": .65, "amenity": .08, "features": .07, "location": .05, "target": .05, "freshness": .05, "quality": .05},
    RankingProfile.INVESTMENT: {"semantic": .30, "amenity": .10, "features": .05, "location": .20, "target": .15, "freshness": .10, "quality": .10},
    RankingProfile.FAMILY: {"semantic": .30, "amenity": .22, "features": .15, "location": .13, "target": .08, "freshness": .05, "quality": .07},
}


def range_fit(value, lower=None, upper=None, target=None) -> float:
    if value is None:
        return 0.0
    value = float(value)
    if target is not None:
        tolerance = max(abs(float(target)) * .25, 1.0)
        return max(0.0, 1 - abs(value - float(target)) / tolerance)
    if lower is not None and value < lower:
        return 0.0
    if upper is not None and value > upper:
        return 0.0
    if lower is None and upper is None:
        return .5
    return 1.0


def freshness_score(value) -> float:
    if not value:
        return .3
    try:
        parsed = datetime.fromisoformat(str(value)).date()
        days = max(0, (date.today() - parsed).days)
        return max(0.0, 1 - days / 365)
    except (TypeError, ValueError):
        return .3


def quality_score(item: dict) -> float:
    score = 1.0
    flags = str(item.get("data_quality_flags") or "")
    if "low_coordinate_confidence" in flags:
        score -= .10
    if "road_snap_over_100m" in flags:
        score -= .05
    if "duplicate_listing_id" in flags:
        score -= .02
    required = ("title", "description", "price_range", "area", "district")
    score -= .03 * sum(item.get(key) in (None, "") for key in required)
    return max(0.0, score)


def _feature_score(item: dict, parsed: ParsedSearchQuery) -> float:
    features = list(parsed.hard_filters.required_features)
    features.extend(pref.value for pref in parsed.soft_preferences if pref.type == "feature" and pref.value)
    if not features:
        return .5
    return sum(bool(item.get(feature)) for feature in set(features)) / len(set(features))


def _amenity_score(item: dict, parsed: ParsedSearchQuery) -> float:
    distances = item.get("amenity_evidence") or []
    if not distances:
        return .5 if not parsed.amenity_filters else 0.0
    scores = []
    for evidence in distances:
        threshold = evidence.get("threshold_km") or 3.0
        distance = evidence.get("driving_distance_km")
        if distance is not None:
            scores.append(max(0.0, 1 - float(distance) / max(float(threshold), .1)))
    return sum(scores) / len(scores) if scores else .5


def rank_candidates(items: Iterable[dict], parsed: ParsedSearchQuery) -> List[dict]:
    weights = WEIGHTS[parsed.ranking_profile]
    results = []
    for item in items:
        semantic = max(0.0, min(1.0, float(item.get("semantic_score") or 0.0)))
        text_score = max(0.0, min(1.0, float(item.get("text_score") or 0.0)))
        semantic = max(semantic, text_score * .85)
        price_range = parsed.hard_filters.price
        area_range = parsed.hard_filters.area
        price = range_fit(item.get("price_range"), price_range.min, price_range.max, price_range.target)
        area = range_fit(item.get("area"), area_range.min, area_range.max, area_range.target)
        target = (price + area) / 2
        features = _feature_score(item, parsed)
        amenity = _amenity_score(item, parsed)
        location = 1.0 if (parsed.hard_filters.districts or parsed.hard_filters.former_admin_areas) else .5
        freshness = freshness_score(item.get("posted_date") or item.get("created_at"))
        quality = quality_score(item)
        breakdown = {"semantic": semantic, "amenity": amenity, "features": features, "location": location, "target": target, "freshness": freshness, "quality": quality}
        final = sum(weights[key] * breakdown[key] for key in weights)
        enriched = dict(item)
        enriched["score_breakdown"] = {key: round(value, 4) for key, value in breakdown.items()}
        enriched["final_score"] = round(final, 4)
        results.append(enriched)
    return sorted(results, key=lambda row: (row["final_score"], row.get("posted_date") or ""), reverse=True)


def diversify(items: List[dict], limit: int, max_per_cluster: int = 3) -> List[dict]:
    selected, cluster_counts = [], {}
    for item in items:
        cluster = item.get("geo_cluster_150m") or f"listing:{item.get('listing_id')}"
        if cluster_counts.get(cluster, 0) >= max_per_cluster:
            continue
        selected.append(item)
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        if len(selected) >= limit:
            break
    return selected
