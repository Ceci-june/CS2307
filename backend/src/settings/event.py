from typing import Callable
from fastapi import FastAPI
from loguru import logger

from src.services.minio.minio_client import MinioClient
from src.services.recommendation.recommendation_service import RecommendationService
from src.services.llm.llm_model import LLModel
from src.services.database.postgresql.connector import PostgresConnector

from src.settings.config import APPLICATION

config = APPLICATION


minio_client = MinioClient(config=APPLICATION)
recommendation_service = RecommendationService()
llm_model = LLModel()
postgres_client = PostgresConnector(config=config)


def create_start_app_handler(app: FastAPI) -> Callable:  # noqa
    async def start_app():
        minio_client.start()
        recommendation_service.start()
        llm_model.start()
        postgres_client.start()
    return start_app


def create_stop_app_handler(app: FastAPI) -> Callable:  # noqa
    @logger.catch
    async def stop_app() -> None:
        minio_client.stop()
        postgres_client.stop()
    return stop_app
