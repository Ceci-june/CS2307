import logging
import os
import sys
from dotenv import dotenv_values, find_dotenv
from loguru import logger

from src.settings.logging_config import InterceptHandler
# load config from .env file
config = dotenv_values(find_dotenv())


def config_value(name, default=None):
    """Prefer process environment (Docker/CI), then values from the local .env."""
    return os.getenv(name, config.get(name, default))

DEBUG = bool(config.get("DEBUG", "False") if config.get(
    "DEBUG", "") in ["True", "true", "1"] else False)

MESSAGE_QUEUE = []

APPLICATION = {
    "version": config.get("VERSION", "1.0.0"),
    "project_name": config.get("PROJECT_NAME"),
    "debug": DEBUG,
    "access_token_secret_key": config.get("ACCESS_TOKEN_SECRET_KEY"),
    "algorithm": config.get("ALGORITHM"),
    "access_token_expire_minutes": config.get("ACCESS_TOKEN_EXPIRE_MINUTES"),
    "refresh_token_secret_key": config.get("REFRESH_TOKEN_SECRET_KEY"),
    "refresh_token_expire_minutes": config.get("REFRESH_TOKEN_EXPIRE_MINUTES"),
    # Minio
    "minio_end_point": config.get("MINIO_END_POINT"),
    "minio_access_key_id": config.get("MINIO_ACCESS_KEY_ID"),
    "minio_secret_access_key": config.get("MINIO_SECRET_ACCESS_KEY"),
    "minio_bucket_name": config.get("MINIO_BUCKET_NAME"),
    "minio_secure": config.get("MINIO_SECURE"),
    "gemini_api_keys": config_value("GEMINI_API_KEYS"),
    # LLM (Gemini or any Chat Completions compatible endpoint)
    "llm_provider": config_value("BACKEND_LLM_PROVIDER", "gemini"),
    "llm_model": config_value("BACKEND_LLM_MODEL"),
    "llm_base_url": config_value("BACKEND_LLM_BASE_URL"),
    "llm_api_key": (
        config_value("BACKEND_LLM_API_KEY")
        or config_value("OPENAI_API_KEY")
        or config_value("GROQ_API_KEY")
        or config_value("XAI_API_KEY")
    ),
    # Postgres
    "host_db": config.get("HOST_DB"),
    "port_db": config.get("PORT_DB"),
    "username_db": config.get("USERNAME_DB"),
    "password_db": config.get("PASSWORD_DB"),
    "database": config.get("DATABASE"),
    # Optional online graph retrieval
    "neo4j_uri": config.get("NEO4J_URI", "bolt://neo4j:7687"),
    "neo4j_user": config.get("NEO4J_USER", "neo4j"),
    "neo4j_password": config.get("NEO4J_PASSWORD"),
    "neo4j_database": config.get("NEO4J_DATABASE", "neo4j"),
    "search_use_neo4j": str(config.get("SEARCH_USE_NEO4J", "false")).lower() in {"1", "true", "yes"},
}

DATE_FORMAT = '%Y-%m-%d'
TIME_FORMAT = '%H:%M:%S'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# logging configuration
LOGGING_LEVEL = logging.DEBUG if APPLICATION["debug"] else logging.INFO
LOGGERS = ("hypercorn.asgi", "hypercorn.access")  # noqa
logger.level("CUSTOM", no=15, color="<blue>", icon="@")
logger.level("SERVICE", no=200)

logging.getLogger().handlers = [InterceptHandler()]

if APPLICATION["debug"]:
    logger.configure(
        handlers=[
            {"sink": sys.stderr, "level": LOGGING_LEVEL},
            {
                "sink": sys.stderr,
                "level": 200,
                "format": "<blue>{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}</blue>",
            },
        ]
    )
else:
    logger.configure(
        handlers=[
            {
                "sink": sys.stderr,
                "level": 200,
                "format": "<blue>{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}</blue>",
            },
        ]
    )

logger.add("./logs/app.log", rotation='10 MB')
