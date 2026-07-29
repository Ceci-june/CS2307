from __future__ import annotations

import time
from typing import Any, Dict

from starlette.concurrency import run_in_threadpool

from src.search.embedding import embedding_model
from src.search.explanation import attach_explanation
from src.search.query_parser import LLMQueryParser, RuleBasedQueryParser
from src.search.ranker import diversify, rank_candidates
from src.search.repository import search_repository
from src.search.schemas import ParsedSearchQuery, SearchRequest
from src.settings.event import llm_model


class HybridSearchService:
    def __init__(self):
        self.rule_parser = RuleBasedQueryParser()
        self.llm_parser = LLMQueryParser(llm_model)

    async def parse(self, query: str, top_k: int = 20, filters: Dict[str, Any] | None = None) -> ParsedSearchQuery:
        deterministic = self.rule_parser.parse(query, top_k=top_k, explicit_filters=filters)
        return await self.llm_parser.parse(query, deterministic)

    async def search(self, request: SearchRequest) -> dict:
        started = time.perf_counter()
        parsed = await self.parse(request.query, request.top_k, request.filters)
        embedded_count, property_count = await run_in_threadpool(search_repository.embedding_coverage)
        vector = None
        if property_count > 0 and embedded_count == property_count:
            vector = await run_in_threadpool(embedding_model.encode_query, parsed.semantic_query)
        query_embedding = None if vector is None else vector.tolist()
        candidate_limit = max(500, request.top_k * request.page * 5)
        candidates = await run_in_threadpool(search_repository.search, parsed, query_embedding, candidate_limit)
        total_candidates = await run_in_threadpool(search_repository.count, parsed)
        relaxations = []
        applied = parsed

        if not candidates and parsed.amenity_filters and not parsed.protected_constraints:
            for distance_factor, duration_factor in ((1.5, 1.25), (2.0, 1.5)):
                trial = parsed.model_copy(deep=True)
                changes = []
                for original, amenity in zip(parsed.amenity_filters, trial.amenity_filters):
                    if original.max_driving_distance_km is not None:
                        amenity.max_driving_distance_km = round(original.max_driving_distance_km * distance_factor, 2)
                        changes.append(
                            f"Mở rộng {amenity.amenity_category} từ {original.max_driving_distance_km:g} km "
                            f"lên {amenity.max_driving_distance_km:g} km"
                        )
                    if original.max_duration_min is not None:
                        amenity.max_duration_min = round(original.max_duration_min * duration_factor, 1)
                        changes.append(
                            f"Mở rộng thời gian tới {amenity.amenity_category} từ {original.max_duration_min:g} "
                            f"lên {amenity.max_duration_min:g} phút"
                        )
                trial_candidates = await run_in_threadpool(
                    search_repository.search, trial, query_embedding, candidate_limit
                )
                if trial_candidates:
                    applied = trial
                    candidates = trial_candidates
                    total_candidates = await run_in_threadpool(search_repository.count, applied)
                    relaxations = changes
                    break

        ranked = rank_candidates(candidates, applied)
        start = (request.page - 1) * request.top_k
        selected = diversify(ranked, start + request.top_k)[start:start + request.top_k]
        results = [attach_explanation(item, applied) for item in selected]
        response = {
            "query": request.query,
            "parsed_query": parsed.model_dump(mode="json"),
            "total_candidates": total_candidates,
            "page": request.page,
            "top_k": request.top_k,
            "results": results,
            "relaxations": relaxations,
            "semantic_enabled": query_embedding is not None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        if request.debug:
            response["debug"] = {
                "retrieved_candidates": len(candidates),
                "ranking_profile": applied.ranking_profile.value,
                "embedding_model": embedding_model.model_name if query_embedding is not None else None,
                "embedding_coverage": {"embedded": embedded_count, "total": property_count},
            }
        return response

    async def similar(self, listing_id: str, top_k: int = 10) -> dict:
        embedded_count, property_count = await run_in_threadpool(search_repository.embedding_coverage)
        if property_count == 0 or embedded_count != property_count:
            return {
                "listing_id": listing_id,
                "results": [],
                "total": 0,
                "available": False,
                "embedding_coverage": {"embedded": embedded_count, "total": property_count},
            }
        items = await run_in_threadpool(search_repository.similar, listing_id, top_k)
        return {"listing_id": listing_id, "results": items, "total": len(items), "available": True}

    async def get_property(self, property_id: str):
        return await run_in_threadpool(search_repository.get_property, property_id)


hybrid_search_service = HybridSearchService()
