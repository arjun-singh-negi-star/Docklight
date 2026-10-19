from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_signup_then_duplicate_then_login(aws_mock):
    resp = client.post("/api/auth/signup", json={"email": "testuser@example.com", "password": "supersecret1"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    dup = client.post("/api/auth/signup", json={"email": "testuser@example.com", "password": "supersecret1"})
    assert dup.status_code == 409

    bad_login = client.post("/api/auth/login", json={"email": "testuser@example.com", "password": "wrongpass"})
    assert bad_login.status_code == 401

    good_login = client.post("/api/auth/login", json={"email": "testuser@example.com", "password": "supersecret1"})
    assert good_login.status_code == 200
    assert good_login.json()["access_token"]


def test_protected_routes_require_a_token(aws_mock):
    resp = client.get("/api/documents")
    assert resp.status_code in (401, 403)
