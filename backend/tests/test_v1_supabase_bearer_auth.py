from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.v1.api.deps import get_current_user
from app.v1.services.auth_service import AuthService


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "headers": [
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in headers.items()
        ],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_uses_supabase_bearer_token(monkeypatch):
    async def fake_resolve(token: str):
        assert token == "token-123"
        return SimpleNamespace(id="user-1", username="alice@example.com", plan="FREE")

    monkeypatch.setattr(
        "app.v1.api.deps.AuthService.resolve_supabase_user",
        fake_resolve,
    )

    user = await get_current_user(
        request=_request_with_headers({"Authorization": "Bearer token-123"}),
    )

    assert user.id == "user-1"
    assert user.username == "alice@example.com"


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_bearer_token_for_supabase(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=_request_with_headers({}),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_resolve_supabase_user_uses_certifi_bundle(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "id": "user-1",
                "email": "alice@example.com",
                "user_metadata": {},
                "app_metadata": {},
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["verify"] = kwargs.get("verify")
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(
        "app.v1.services.auth_service.settings",
        SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_secret_key="secret-key",
        ),
    )
    monkeypatch.setattr("app.v1.services.auth_service.httpx.AsyncClient", DummyClient)

    user = await AuthService.resolve_supabase_user("token-123")

    assert user.id == "user-1"
    assert captured["url"] == "https://example.supabase.co/auth/v1/user"
    assert captured["headers"]["Authorization"] == "Bearer token-123"
    assert captured["headers"]["apikey"] == "secret-key"
    assert str(captured["verify"]).endswith("cacert.pem")
