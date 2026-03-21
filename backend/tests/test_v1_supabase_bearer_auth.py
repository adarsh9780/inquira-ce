from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.v1.api.deps import get_current_user


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
