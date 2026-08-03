"""Parameterized SQL for feedback capture (interactions + impressions)."""

from __future__ import annotations

from typing import List, Optional

from src.settings.event import postgres_client


def insert_interaction(
    user_id: Optional[int],
    session_id: Optional[str],
    listing_id: Optional[int],
    action_type: str,
    source: Optional[str],
    dwell_time_seconds: Optional[float],
    implicit_score: float,
    raw_query: Optional[str],
    conversation_id: Optional[int],
) -> dict:
    rows = postgres_client.fetch_write(
        "INSERT INTO interactions "
        "(user_id, session_id, listing_id, action_type, source, dwell_time_seconds, "
        " implicit_score, raw_query, conversation_id) "
        "VALUES (:user_id, :session_id, :listing_id, :action_type, :source, "
        " :dwell_time_seconds, :implicit_score, :raw_query, :conversation_id) "
        "RETURNING id, created_at",
        user_id=user_id,
        session_id=session_id,
        listing_id=listing_id,
        action_type=action_type,
        source=source,
        dwell_time_seconds=dwell_time_seconds,
        implicit_score=implicit_score,
        raw_query=raw_query,
        conversation_id=conversation_id,
    )
    return rows[0]


def insert_recommendation_events(rows: List[dict]) -> int:
    """Bulk-insert one impression row per shown listing. Best-effort."""
    return postgres_client.execute_write_many(
        "INSERT INTO recommendation_events "
        "(result_set_id, user_id, session_id, conversation_id, raw_query, "
        " algorithm_version, listing_id, retrieval_rank, score, llm_chosen, llm_rank) "
        "VALUES (:result_set_id, :user_id, :session_id, :conversation_id, :raw_query, "
        " :algorithm_version, :listing_id, :retrieval_rank, :score, :llm_chosen, :llm_rank)",
        rows,
    )


def get_recent_interactions(user_id: int, limit: int = 200) -> List[dict]:
    """Most recent positive-signal interactions for building a user profile."""
    return postgres_client.fetch_mappings(
        "SELECT i.listing_id, i.action_type, i.implicit_score, "
        "       p.district, p.property_type, p.price_range "
        "FROM interactions i "
        "LEFT JOIN properties p ON p.listing_id = i.listing_id "
        "WHERE i.user_id = :user_id AND i.implicit_score > 0 "
        "ORDER BY i.created_at DESC LIMIT :limit",
        user_id=user_id,
        limit=limit,
    )
