from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from src.search.personalization import score_item as personalization_score
from src.search.schemas import ParsedSearchQuery, RankingProfile


# How much a user's feedback profile can shift a listing's score. Kept modest so
# personalization nudges rather than overrides the deterministic ranking.
PERSONALIZATION_WEIGHT = 0.15

# Graded falloff width for an approximate numeric target. Kept a touch wider than
# the retrieval band (repository.PRICE_AREA_TOLERANCE = 0.15) so every listing that
# survives the filter still scores positively, degrading smoothly toward the edge.
RANK_TARGET_TOLERANCE = 0.25


WEIGHTS: Dict[RankingProfile, Dict[str, float]] = {
    RankingProfile.BALANCED: {"semantic": .36, "graph": .14, "amenity": .13, "features": .10, "location": .10, "target": .08, "freshness": .05, "quality": .04},
    RankingProfile.LOCATION_FIRST: {"semantic": .21, "graph": .19, "amenity": .25, "features": .07, "location": .16, "target": .06, "freshness": .03, "quality": .03},
    RankingProfile.AMENITY_FIRST: {"semantic": .20, "graph": .20, "amenity": .31, "features": .11, "location": .06, "target": .04, "freshness": .04, "quality": .04},
    RankingProfile.PRICE_FIRST: {"semantic": .21, "graph": .08, "amenity": .08, "features": .07, "location": .07, "target": .30, "freshness": .10, "quality": .09},
    RankingProfile.SEMANTIC_FIRST: {"semantic": .56, "graph": .10, "amenity": .07, "features": .06, "location": .05, "target": .05, "freshness": .05, "quality": .06},
    RankingProfile.INVESTMENT: {"semantic": .25, "graph": .13, "amenity": .09, "features": .05, "location": .18, "target": .13, "freshness": .08, "quality": .09},
    RankingProfile.FAMILY: {"semantic": .25, "graph": .17, "amenity": .18, "features": .13, "location": .11, "target": .07, "freshness": .04, "quality": .05},
}


def range_fit(value, lower=None, upper=None, target=None) -> float:
    if value is None:
        return 0.0
    value = float(value)
    if target is not None:
        tolerance = max(abs(float(target)) * RANK_TARGET_TOLERANCE, 1.0)
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
    weighted_features = {feature: 1.0 for feature in parsed.hard_filters.required_features}
    for preference in parsed.soft_preferences:
        if preference.type == "feature" and preference.value:
            weighted_features[preference.value] = max(
                weighted_features.get(preference.value, 0.0), preference.weight
            )
    if not weighted_features:
        return .5
    total_weight = sum(weighted_features.values())
    return sum(weight * bool(item.get(feature)) for feature, weight in weighted_features.items()) / total_weight


def _amenity_score(item: dict, parsed: ParsedSearchQuery) -> float:
    distances = item.get("amenity_evidence") or []
    if not parsed.amenity_filters:
        return .5
    scores = []
    for preference in parsed.amenity_filters:
        matching = [item for item in distances if item.get("category") == preference.amenity_category]
        candidate_scores = []
        for evidence in matching:
            if preference.max_driving_distance_km is not None and evidence.get("driving_distance_km") is not None:
                limit = max(float(preference.max_driving_distance_km), .1)
                candidate_scores.append(max(0.0, 1 - float(evidence["driving_distance_km"]) / limit))
            elif preference.max_duration_min is not None and evidence.get("driving_duration_min") is not None:
                limit = max(float(preference.max_duration_min), 1.0)
                candidate_scores.append(max(0.0, 1 - float(evidence["driving_duration_min"]) / limit))
            else:
                candidate_scores.append(1.0)
        scores.append(max(candidate_scores, default=0.0))
    return sum(scores) / len(scores) if scores else 0.0


def rank_candidates(
    items: Iterable[dict],
    parsed: ParsedSearchQuery,
    user_profile: Optional[Dict[str, Any]] = None,
) -> List[dict]:
    weights = WEIGHTS[parsed.ranking_profile]
    results = []
    for item in items:
        semantic = max(0.0, min(1.0, float(item.get("semantic_score") or 0.0)))
        text_score = max(0.0, min(1.0, float(item.get("text_score") or 0.0)))
        semantic = max(semantic, text_score * .85)
        graph = max(0.0, min(1.0, float(item.get("graph_score", 0.5))))
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
        breakdown = {"semantic": semantic, "graph": graph, "amenity": amenity, "features": features, "location": location, "target": target, "freshness": freshness, "quality": quality}
        final = sum(weights[key] * breakdown[key] for key in weights)
        enriched = dict(item)
        # Blend in a personalization term only when a user profile exists, so the
        # anonymous ranking is identical to before.
        if user_profile is not None:
            personalization = personalization_score(item, user_profile)
            breakdown["personalization"] = personalization
            final = (1 - PERSONALIZATION_WEIGHT) * final + PERSONALIZATION_WEIGHT * personalization
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
