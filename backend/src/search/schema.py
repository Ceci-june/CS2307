from __future__ import annotations

from pathlib import Path

from loguru import logger
from sqlalchemy import text

from src.settings.event import postgres_client


def initialize_search_schema() -> None:
    migration = Path(__file__).resolve().parents[2] / "migrations" / "001_pgvector_hybrid_search.sql"
    if not migration.exists():
        raise RuntimeError(f"Search migration not found: {migration}")
    statements = [statement.strip() for statement in migration.read_text(encoding="utf-8").split(";") if statement.strip()]
    # Gunicorn workers start concurrently. One transaction-scoped advisory lock keeps
    # CREATE EXTENSION/INDEX idempotent in practice as well as in SQL syntax.
    with postgres_client.engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(2307001)"))
        for statement in statements:
            connection.execute(text(statement))
    logger.info("PostgreSQL/pgvector search schema is ready")
