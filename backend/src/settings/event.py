from typing import Callable
from fastapi import FastAPI
from loguru import logger

from src.services.minio.minio_client import MinioClient
from src.services.llm.llm_model import LLModel
from src.services.database.postgresql.connector import PostgresConnector

from src.settings.config import APPLICATION

config = APPLICATION


minio_client = MinioClient(config=APPLICATION)
llm_model = LLModel()
postgres_client = PostgresConnector(config=config)


class LegacyRecommendationAdapter:
    """Compatibility bridge for the deprecated /properties/ai-search endpoint."""

    async def ai_recommendation(self, question: str, **filters):
        from src.search.schemas import SearchRequest
        from src.search.service import hybrid_search_service

        request = SearchRequest(query=question, top_k=3, filters=filters)
        response = await hybrid_search_service.search(request)
        return True, response["results"], None

    def start(self):
        return None


recommendation_service = LegacyRecommendationAdapter()


def create_start_app_handler(app: FastAPI) -> Callable:  # noqa
    async def start_app():
        minio_client.start()
        recommendation_service.start()
        llm_model.start()
        postgres_client.start()
        from src.search.graph_repository import graph_repository
        graph_repository.start()
    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:  # noqa
    @logger.catch
    async def stop_app() -> None:
        from src.search.graph_repository import graph_repository
        graph_repository.stop()
        minio_client.stop()
        postgres_client.stop()
    return stop_app
