"""
Single shared Redis client, used for caching, rate limiting, and as the
Celery broker/backend. Kept as one lazily-constructed module-level client
so every service reuses the same connection pool.

Tests can swap in a fake client (e.g. fakeredis) via
reset_redis_client_for_tests() instead of needing a real Redis server.
"""
import redis

from app.config import get_settings

_client = None


def get_redis():
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def reset_redis_client_for_tests(client) -> None:
    """Test-only hook to inject a fake Redis client (e.g. fakeredis.FakeStrictRedis())."""
    global _client
    _client = client
