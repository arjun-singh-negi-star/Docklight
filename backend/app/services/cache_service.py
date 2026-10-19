"""
Caches identical (user, question) pairs for a short TTL so repeated or
accidental double-submits don't re-run embeddings + retrieval + an LLM call.
Keyed per-user so one person's cache never leaks an answer to another.
"""
import hashlib
import json

from app.services.redis_client import get_redis


def _cache_key(user_id: str, question: str) -> str:
    normalized = question.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"chatcache:{user_id}:{digest}"


def get_cached_answer(user_id: str, question: str) -> dict | None:
    raw = get_redis().get(_cache_key(user_id, question))
    return json.loads(raw) if raw else None


def set_cached_answer(user_id: str, question: str, payload: dict, ttl_seconds: int) -> None:
    get_redis().setex(_cache_key(user_id, question), ttl_seconds, json.dumps(payload))
