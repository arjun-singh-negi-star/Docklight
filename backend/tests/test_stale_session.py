from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.main import app

client = TestClient(app)


def test_valid_token_for_unknown_user_gets_401_not_500(aws_mock):
    # Simulates a browser holding an old token after the (fake) AWS data was wiped:
    # the token is cryptographically valid, but the users table doesn't even exist.
    token = create_access_token("ghost-user")
    resp = client.get("/api/documents", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_health_treats_missing_bucket_as_healthy(aws_mock, fake_redis):
    # The bucket is created lazily on first upload, so a fresh install must not look "degraded".
    body = client.get("/health").json()
    s3 = next(c for c in body["components"] if c["name"] == "s3")
    assert s3["healthy"] is True
