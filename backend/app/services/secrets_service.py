"""
Loads secrets either from AWS Secrets Manager (production, USE_SECRETS_MANAGER=true)
or from plain environment variables (local dev / fake-data mode). Route and
service code never needs to know which source is active.
"""
import json
from functools import lru_cache

from app.config import get_settings
from app.services.aws_clients import get_secrets_manager_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def load_secrets() -> dict:
    settings = get_settings()
    if not settings.USE_SECRETS_MANAGER:
        return {"PINECONE_API_KEY": settings.PINECONE_API_KEY}

    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=settings.SECRETS_MANAGER_SECRET_NAME)
        return json.loads(response["SecretString"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not load secrets from Secrets Manager, falling back to env vars: %s", exc)
        return {"PINECONE_API_KEY": settings.PINECONE_API_KEY}
