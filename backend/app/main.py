from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, documents, health, metrics
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=(
        "RAG API powered by AWS Bedrock, S3, DynamoDB and Pinecone, with JWT "
        "auth, per-user multi-tenancy, async ingestion via Celery, hybrid "
        "retrieval, conversation memory, and Redis-backed caching/rate limiting."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "status": "running"}
