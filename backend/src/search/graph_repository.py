from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from dotenv import dotenv_values, find_dotenv

from src.search.normalizer import FEATURE_ALIASES, normalize_text
from src.search.schemas import ParsedSearchQuery

logger = logging.getLogger(__name__)
_ENV = {**dotenv_values(find_dotenv()), **os.environ}

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - exercised only in a misconfigured runtime
    GraphDatabase = None


GRAPH_FEATURE_CATEGORIES = {
    "near_metro": {"metro"},
    "near_bus": {"bus_stop"},
    "near_school": {"school", "college_university"},
    "near_hospital": {"hospital"},
    "near_mall": {"mall", "supermarket"},
    "near_market": {"market"},
    "near_park": {"park"},
}


@dataclass
class GraphSearchResponse:
    available: bool
    candidates: List[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None


class Neo4jGraphRepository:
    """Optional Neo4j retrieval source.

    PostgreSQL remains the source of truth for listing payloads. Neo4j contributes
    candidate IDs, relationship-derived scores and explainable graph evidence.
    """

    def __init__(self) -> None:
        self.enabled = str(_ENV.get("SEARCH_USE_NEO4J", "false")).lower() in {"1", "true", "yes"}
        self.uri = _ENV.get("NEO4J_URI", "bolt://neo4j:7687")
        self.user = _ENV.get("NEO4J_USER", "neo4j")
        self.password = _ENV.get("NEO4J_PASSWORD")
        self.database = _ENV.get("NEO4J_DATABASE", "neo4j")
        self._driver = None
        self._lock = Lock()
        self._last_connect_attempt = 0.0

    def start(self) -> bool:
        if not self.enabled:
            return False
        if self._driver is not None:
            return True
        if GraphDatabase is None:
            logger.warning("Neo4j graph search disabled: Python neo4j driver is not installed")
            return False
        with self._lock:
            if self._driver is not None:
                return True
            self._last_connect_attempt = time.monotonic()
            driver = None
            try:
                driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    connection_timeout=3,
                    max_connection_pool_size=20,
                )
                driver.verify_connectivity()
                self._driver = driver
                logger.info("Neo4j graph search is ready")
                return True
            except Exception as exc:
                if driver is not None:
                    driver.close()
                logger.warning(f"Neo4j graph search unavailable; PostgreSQL fallback remains active: {exc}")
                return False

    def stop(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _ensure_driver(self) -> bool:
        if self._driver is not None:
            return True
        # Permit recovery when Neo4j starts after the API without reconnecting on
        # every request while the graph service is down.
        if time.monotonic() - self._last_connect_attempt < 30:
            return False
        return self.start()

    @staticmethod
    def _query(parsed: ParsedSearchQuery) -> Tuple[str, Dict[str, Any]]:
        hard = parsed.hard_filters
        where = []
        params: Dict[str, Any] = {}

        numeric = (
            ("price_range", "price", hard.price),
            ("area", "area", hard.area),
            ("bedrooms", "bedrooms", hard.bedrooms),
            ("bathrooms", "bathrooms", hard.bathrooms),
        )
        for prop, key, value in numeric:
            if value.min is not None:
                where.append(f"l.{prop} >= ${key}_min")
                params[f"{key}_min"] = value.min
            if value.max is not None:
                where.append(f"l.{prop} <= ${key}_max")
                params[f"{key}_max"] = value.max

        list_filters = (
            ("property_type", hard.property_types),
            ("legal_status", hard.legal_statuses),
            ("furnishing", hard.furnishings),
            ("house_direction", hard.house_directions),
            ("balcony_direction", hard.balcony_directions),
        )
        for prop, values in list_filters:
            if values:
                key = f"{prop}_values"
                where.append(f"toLower(l.{prop}) IN ${key}")
                params[key] = [value.lower() for value in values]
        if hard.excluded_property_types:
            where.append("NOT toLower(l.property_type) IN $excluded_property_types")
            params["excluded_property_types"] = [value.lower() for value in hard.excluded_property_types]

        location_values = [*hard.districts, *hard.former_admin_areas]
        if location_values:
            location_terms_set = set()
            for value in location_values:
                normalized = normalize_text(value)
                location_terms_set.update({value.lower(), normalized})
                short_name = re.sub(
                    r"^(?:phuong|xa|quan|huyen|thi xa|thanh pho|tp)\s+",
                    "",
                    normalized,
                )
                if short_name:
                    location_terms_set.add(short_name)
            location_terms = sorted(term for term in location_terms_set if term)
            where.append(
                "(toLower(l.ward_commune) IN $location_terms OR "
                "toLower(l.former_admin_area) IN $location_terms OR "
                "EXISTS { MATCH (l)-[:IN_WARD]->(wa:Ward) "
                "WHERE toLower(wa.ward_type + ' ' + wa.name) IN $location_terms "
                "OR wa.normalized_name IN $location_terms "
                "OR any(alias IN split(coalesce(wa.aliases, ''), '|') "
                "WHERE toLower(alias) IN $location_terms) } OR "
                "EXISTS { MATCH (l)-[:IN_FORMER_AREA]->(fa:FormerAdminArea) "
                "WHERE toLower(fa.name) IN $location_terms "
                "OR fa.normalized_name IN $location_terms "
                "OR any(alias IN split(coalesce(fa.aliases, ''), '|') "
                "WHERE toLower(alias) IN $location_terms) })"
            )
            params["location_terms"] = location_terms

        for feature in hard.required_features:
            if feature in GRAPH_FEATURE_CATEGORIES:
                key = f"required_{feature}_categories"
                where.append(
                    f"EXISTS {{ MATCH (l)-[:NEAR_AMENITY]->(required_{feature}:Amenity) "
                    f"WHERE required_{feature}.category IN ${key} }}"
                )
                params[key] = sorted(GRAPH_FEATURE_CATEGORIES[feature])
            elif feature in FEATURE_ALIASES:
                where.append(f"coalesce(l.{feature}, false) = true")
        for feature in hard.excluded_features:
            if feature in GRAPH_FEATURE_CATEGORIES:
                key = f"excluded_{feature}_categories"
                where.append(
                    f"NOT EXISTS {{ MATCH (l)-[:NEAR_AMENITY]->(excluded_{feature}:Amenity) "
                    f"WHERE excluded_{feature}.category IN ${key} }}"
                )
                params[key] = sorted(GRAPH_FEATURE_CATEGORIES[feature])
            elif feature in FEATURE_ALIASES:
                where.append(f"coalesce(l.{feature}, false) = false")

        for index, amenity in enumerate(parsed.amenity_filters):
            if not amenity.required:
                continue
            clauses = [f"a{index}.category = $amenity_category_{index}"]
            params[f"amenity_category_{index}"] = amenity.amenity_category
            if amenity.max_driving_distance_km is not None:
                clauses.append(f"r{index}.driving_distance_km <= $amenity_distance_{index}")
                params[f"amenity_distance_{index}"] = amenity.max_driving_distance_km
            if amenity.max_duration_min is not None:
                clauses.append(f"r{index}.driving_duration_min <= $amenity_duration_{index}")
                params[f"amenity_duration_{index}"] = amenity.max_duration_min
            where.append(
                f"EXISTS {{ MATCH (l)-[r{index}:NEAR_AMENITY]->(a{index}:Amenity) "
                f"WHERE {' AND '.join(clauses)} }}"
            )

        requested_features = {
            *hard.required_features,
            *(pref.value for pref in parsed.soft_preferences if pref.type == "feature" and pref.value),
        }
        preference_features = sorted(
            {
                *requested_features,
            }
            & (set(FEATURE_ALIASES) - set(GRAPH_FEATURE_CATEGORIES))
        )
        amenity_categories = {item.amenity_category for item in parsed.amenity_filters}
        for feature in requested_features:
            amenity_categories.update(GRAPH_FEATURE_CATEGORIES.get(feature, set()))
        params.update(
            {
                "preference_features": preference_features,
                "amenity_categories": sorted(amenity_categories),
                "candidate_limit": 500,
            }
        )
        where_sql = " AND ".join(where) if where else "true"
        query = f"""
            MATCH (l:Listing)
            WHERE {where_sql}
            OPTIONAL MATCH (l)-[:IN_WARD]->(w:Ward)
            OPTIONAL MATCH (l)-[:IN_FORMER_AREA]->(former:FormerAdminArea)
            OPTIONAL MATCH (l)-[near:NEAR_AMENITY]->(a:Amenity)
            WHERE size($amenity_categories) = 0 OR a.category IN $amenity_categories
            WITH l, collect(DISTINCT w.name) AS wards,
                 collect(DISTINCT former.name) AS former_areas,
                 collect(DISTINCT CASE WHEN a IS NULL THEN null ELSE {{
                     category: a.category, name: a.name,
                     driving_distance_km: near.driving_distance_km,
                     driving_duration_min: near.driving_duration_min,
                     threshold_km: near.threshold_km
                 }} END) AS amenities
            RETURN toString(l.listing_id) AS listing_id,
                   l.listing_node_id AS listing_node_id,
                   wards,
                   [x IN amenities WHERE x IS NOT NULL] AS amenities,
                   [feature IN $preference_features WHERE coalesce(l[feature], false)] AS matched_features,
                   coalesce(head(former_areas), l.former_admin_area) AS former_admin_area,
                   l.geo_cluster_150m AS geo_cluster_150m
            ORDER BY coalesce(l.posted_date, date('1970-01-01')) DESC
            LIMIT $candidate_limit
        """
        return query, params

    @staticmethod
    def _score_record(record: dict, parsed: ParsedSearchQuery) -> dict:
        requested_features = {
            *parsed.hard_filters.required_features,
            *(pref.value for pref in parsed.soft_preferences if pref.type == "feature" and pref.value),
        }
        matched_features = set(record.get("matched_features") or [])
        evidence = record.get("amenities") or []
        evidence_categories = {item.get("category") for item in evidence}
        for feature, categories in GRAPH_FEATURE_CATEGORIES.items():
            if feature in requested_features and categories & evidence_categories:
                matched_features.add(feature)
        components = []
        if requested_features:
            components.append(len(matched_features & requested_features) / len(requested_features))

        requested_amenities = {item.amenity_category: item for item in parsed.amenity_filters}
        if requested_amenities:
            amenity_scores = []
            for category, preference in requested_amenities.items():
                matches = [item for item in evidence if item.get("category") == category]
                if not matches:
                    amenity_scores.append(0.0)
                    continue
                best = 0.0
                for item in matches:
                    if preference.max_driving_distance_km is not None and item.get("driving_distance_km") is not None:
                        limit = max(float(preference.max_driving_distance_km), 0.1)
                        best = max(best, max(0.0, 1 - float(item["driving_distance_km"]) / limit))
                    elif preference.max_duration_min is not None and item.get("driving_duration_min") is not None:
                        limit = max(float(preference.max_duration_min), 1.0)
                        best = max(best, max(0.0, 1 - float(item["driving_duration_min"]) / limit))
                    else:
                        best = 1.0
                amenity_scores.append(best)
            components.append(sum(amenity_scores) / len(amenity_scores))

        if parsed.hard_filters.districts or parsed.hard_filters.former_admin_areas:
            components.append(1.0)
        graph_score = sum(components) / len(components) if components else 0.5
        return {
            "listing_id": str(record["listing_id"]),
            "graph_score": round(graph_score, 4),
            "graph_evidence": {
                "listing_node_id": record.get("listing_node_id"),
                "wards": record.get("wards") or [],
                "former_admin_area": record.get("former_admin_area"),
                "matched_features": sorted(matched_features),
                "amenities": evidence,
            },
        }

    def search(self, parsed: ParsedSearchQuery, candidate_limit: int = 500) -> GraphSearchResponse:
        started = time.perf_counter()
        if not self.enabled:
            return GraphSearchResponse(available=False, error="disabled")
        if not self._ensure_driver():
            return GraphSearchResponse(available=False, error="unavailable")
        query, params = self._query(parsed)
        params["candidate_limit"] = min(max(candidate_limit, parsed.top_k), 1000)
        try:
            with self._driver.session(database=self.database, default_access_mode="READ") as session:
                records = [dict(record) for record in session.run(query, params)]
            candidates = [self._score_record(record, parsed) for record in records]
            return GraphSearchResponse(
                available=True,
                candidates=candidates,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:
            logger.warning(f"Neo4j graph retrieval failed; using PostgreSQL candidates only: {exc}")
            return GraphSearchResponse(
                available=False,
                error=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )

    def similar(self, listing_id: str, limit: int = 10) -> GraphSearchResponse:
        """Find listings connected through shared place and amenity nodes."""
        started = time.perf_counter()
        if not self.enabled:
            return GraphSearchResponse(available=False, error="disabled")
        if not self._ensure_driver():
            return GraphSearchResponse(available=False, error="unavailable")
        query = """
            MATCH (source:Listing)
            WHERE toString(source.listing_id) = $listing_id
               OR source.listing_node_id = $listing_id
            WITH source LIMIT 1
            MATCH (source)-[source_rel:IN_WARD|ON_STREET|IN_CLUSTER|NEAR_AMENITY]->(shared)
                  <-[candidate_rel:IN_WARD|ON_STREET|IN_CLUSTER|NEAR_AMENITY]-(candidate:Listing)
            WHERE candidate <> source
            WITH candidate,
                 count(DISTINCT shared) AS shared_count,
                 collect(DISTINCT CASE
                     WHEN shared:Ward THEN {type: 'ward', name: shared.name}
                     WHEN shared:Street THEN {type: 'street', name: shared.name}
                     WHEN shared:GeoCluster THEN {type: 'geo_cluster', name: shared.cluster_id}
                     WHEN shared:Amenity THEN {type: 'amenity', name: shared.name, category: shared.category}
                 END) AS shared_evidence
            RETURN toString(candidate.listing_id) AS listing_id,
                   candidate.listing_node_id AS listing_node_id,
                   shared_count,
                   [x IN shared_evidence WHERE x IS NOT NULL] AS shared_evidence
            ORDER BY shared_count DESC, coalesce(candidate.posted_date, date('1970-01-01')) DESC
            LIMIT $limit
        """
        try:
            params = {"listing_id": str(listing_id), "limit": min(max(limit * 3, limit), 150)}
            with self._driver.session(database=self.database, default_access_mode="READ") as session:
                records = [dict(record) for record in session.run(query, params)]
            candidates = []
            for record in records:
                row = record
                candidates.append(
                    {
                        "listing_id": str(row["listing_id"]),
                        "graph_score": round(min(1.0, float(row["shared_count"]) / 5.0), 4),
                        "graph_evidence": {
                            "listing_node_id": row.get("listing_node_id"),
                            "shared_count": row.get("shared_count"),
                            "shared_relationships": row.get("shared_evidence") or [],
                        },
                    }
                )
            return GraphSearchResponse(
                available=True,
                candidates=candidates,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
        except Exception as exc:
            logger.warning(f"Neo4j similar-listing traversal failed: {exc}")
            return GraphSearchResponse(
                available=False,
                error=str(exc),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )


graph_repository = Neo4jGraphRepository()
