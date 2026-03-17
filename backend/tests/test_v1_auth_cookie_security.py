from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def _credentials():
    return {
        "username": f"user_{uuid4().hex[:10]}",
        "password": "secret123",
    }


def test_auth_cookie_not_secure_for_localhost():
    creds = _credentials()
    with TestClient(app, base_url="http://localhost:8000") as client:
        response = client.post("/api/v1/auth/register", json=creds)
    assert response.status_code == 200
    cookie_header = str(response.headers.get("set-cookie") or "")
    assert "session_token=" in cookie_header
    assert "Secure" not in cookie_header


def test_auth_cookie_secure_for_non_local_host():
    creds = _credentials()
    with TestClient(app, base_url="https://app.inquira.dev") as client:
        response = client.post("/api/v1/auth/register", json=creds)
    assert response.status_code == 200
    cookie_header = str(response.headers.get("set-cookie") or "")
    assert "session_token=" in cookie_header
    assert "Secure" in cookie_header
