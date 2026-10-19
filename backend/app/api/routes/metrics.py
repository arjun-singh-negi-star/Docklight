"""Prometheus metrics, scraped by Kubernetes / Prometheus at /metrics."""
from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

router = APIRouter(tags=["metrics"])

CHAT_REQUESTS = Counter("docklight_chat_requests_total", "Total chat query requests")
CHAT_CACHE_HITS = Counter("docklight_chat_cache_hits_total", "Chat requests answered from cache")
CHAT_LATENCY = Histogram("docklight_chat_latency_seconds", "Chat query latency in seconds")
DOCUMENTS_INDEXED = Counter("docklight_documents_indexed_total", "Documents successfully indexed")
DOCUMENTS_FAILED = Counter("docklight_documents_failed_total", "Documents that failed processing")


@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
