import pytest
from fastapi import HTTPException

from app.services.cache_service import get_cached_answer, set_cached_answer
from app.services.rate_limiter import enforce_rate_limit


def test_rate_limit_allows_then_blocks(fake_redis):
    for _ in range(3):
        enforce_rate_limit("user1", limit=3)
    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit("user1", limit=3)
    assert exc_info.value.status_code == 429


def test_rate_limit_is_scoped_per_identifier(fake_redis):
    for _ in range(3):
        enforce_rate_limit("userA", limit=3)
    enforce_rate_limit("userB", limit=3)  # a different user must not be blocked


def test_cache_roundtrip_and_miss(fake_redis):
    assert get_cached_answer("user1", "What is the refund policy?") is None
    payload = {"answer": "14 days", "sources": [], "conversation_id": "c1"}
    set_cached_answer("user1", "What is the refund policy?", payload, ttl_seconds=60)
    assert get_cached_answer("user1", "What is the refund policy?") == payload


def test_cache_key_ignores_case_and_whitespace(fake_redis):
    payload = {"answer": "14 days", "sources": [], "conversation_id": "c1"}
    set_cached_answer("user1", "  What is the refund policy?  ", payload, ttl_seconds=60)
    assert get_cached_answer("user1", "what is the refund policy?") == payload
