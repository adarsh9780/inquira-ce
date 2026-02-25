from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.v1.repositories.auth_repository import AuthSessionRecord
from app.v1.services.auth_service import AuthService


class DummySession:
    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_resolve_user_from_session_rejects_unknown_session(monkeypatch):
    class FakeRepo:
        async def get_session(self, _token):
            return None

    monkeypatch.setattr(
        "app.v1.services.auth_service.get_auth_repository",
        lambda _session: FakeRepo(),
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.resolve_user_from_session(DummySession(), "missing-token")

    assert exc.value.status_code == 401
    assert "Invalid session" in exc.value.detail


@pytest.mark.asyncio
async def test_logout_deletes_session(monkeypatch):
    deleted = {}

    class FakeRepo:
        async def delete_session(self, token):
            deleted["token"] = token

    monkeypatch.setattr(
        "app.v1.services.auth_service.get_auth_repository",
        lambda _session: FakeRepo(),
    )

    await AuthService.logout(DummySession(), "token-123")
    assert deleted["token"] == "token-123"


@pytest.mark.asyncio
async def test_resolve_user_from_session_uses_repository_boundary(monkeypatch):
    class FakeRepo:
        async def get_session(self, _token):
            return AuthSessionRecord(
                session_token="session-1",
                user_id="user-1",
                created_at=datetime.now(timezone.utc),
            )

        async def get_by_id(self, user_id):
            return type(
                "AuthUser",
                (),
                {
                    "id": user_id,
                    "username": "alice",
                    "password_hash": "x",
                    "salt": "y",
                    "plan": "FREE",
                },
            )()

    monkeypatch.setattr(
        "app.v1.services.auth_service.get_auth_repository",
        lambda _session: FakeRepo(),
    )

    user = await AuthService.resolve_user_from_session(DummySession(), "session-1")
    assert user.id == "user-1"
