"""
Simple fixed-window rate limiter backed by Redis, used as a FastAPI
dependency on expensive endpoints (chat queries). A fixed window is a
little bursty at window edges compared to a sliding log, but it's O(1) per
request and easy to reason about -- the right tradeoff for this scale.
"""
import time

from fastapi import HTTPException, status

from app.services.redis_client import get_redis


def enforce_rate_limit(identifier: str, limit: int, window_seconds: int = 60) -> None:
    r = get_redis()
    window = int(time.time() // window_seconds)
    key = f"ratelimit:{identifier}:{window}"

    current = r.incr(key)
    if current == 1:
        r.expire(key, window_seconds)

    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {limit} requests per {window_seconds}s.",
        )
