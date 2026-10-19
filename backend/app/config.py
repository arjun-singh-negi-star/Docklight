"""
Central application configuration.

Everything is read from environment variables so the exact same image works:
  - on your laptop (via a .env file + docker-compose),
  - inside Docker,
  - inside Kubernetes (values injected from a ConfigMap + Secret).

Nothing here should ever hold a real credential — see .env.example.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- App ----
    APP_NAME: str = "Docklight RAG API"
    APP_ENV: str = "development"          # development | staging | production
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "*"

    # ---- AWS ----
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    # Set to http://localstack:4566 for local/fake-data testing (Phase 2).
    # Leave empty to hit real AWS using the credentials above or an IAM role.
    AWS_ENDPOINT_URL: str | None = None
    S3_BUCKET_NAME: str = "rag-documents-bucket"
    DYNAMODB_TABLE_NAME: str = "rag-documents-metadata"
    USERS_TABLE_NAME: str = "rag-users"
    CONVERSATIONS_TABLE_NAME: str = "rag-conversations"

    # ---- AWS Bedrock (embeddings + LLM). Bedrock always calls real AWS,
    # even when AWS_ENDPOINT_URL points at LocalStack, because LocalStack's
    # free tier does not emulate model invocation. ----
    BEDROCK_REGION: str = "us-east-1"
    # Dedicated real-AWS credentials used ONLY for Bedrock. Needed in docker-compose
    # fake-data mode, where AWS_ACCESS_KEY_ID/SECRET are fake LocalStack values.
    BEDROCK_ACCESS_KEY_ID: str | None = None
    BEDROCK_SECRET_ACCESS_KEY: str | None = None
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_LLM_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    EMBEDDING_DIMENSION: int = 1024

    # ---- Provider switches (default = AWS Bedrock; flip in .env, no code change) ----
    # EMBEDDING_PROVIDER: "bedrock" | "pinecone" (Pinecone's own hosted embedding models)
    # LLM_PROVIDER: "bedrock" | "openai_compatible" (OpenAI, Groq, Gemini's OpenAI endpoint, Ollama...)
    # NOTE: never mix embedding providers inside one Pinecone index -- vectors from different
    # models aren't comparable. Use a different PINECONE_INDEX_NAME when you switch.
    EMBEDDING_PROVIDER: str = "bedrock"
    PINECONE_EMBEDDING_MODEL: str = "multilingual-e5-large"
    LLM_PROVIDER: str = "bedrock"
    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str | None = None

    # ---- Pinecone ----
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str = "rag-knowledge-base"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"

    # ---- Secrets Manager (production only) ----
    USE_SECRETS_MANAGER: bool = False
    SECRETS_MANAGER_SECRET_NAME: str = "rag-app/prod/secrets"

    # ---- Chunking / retrieval ----
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    TOP_K_RESULTS: int = 4
    RETRIEVAL_CANDIDATE_MULTIPLIER: int = 3   # fetch top_k * this many candidates before reranking
    HYBRID_ALPHA: float = 0.5                 # weight of vector similarity vs. lexical (BM25) score, 0..1

    # ---- Auth ----
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ---- Redis (cache, rate limiting, Celery broker/backend) ----
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 20
    CACHE_TTL_SECONDS: int = 3600
    CONVERSATION_HISTORY_TURNS: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
