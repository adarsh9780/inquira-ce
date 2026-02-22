import pytest
from fastapi import HTTPException

from app.v1.services.auth_service import AuthService


class DummySession:
    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_resolve_user_from_session_rejects_unknown_session(monkeypatch):
    async def fake_get_session(_session, _token):
        return None

    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.get_session", fake_get_session)

    with pytest.raises(HTTPException) as exc:
        await AuthService.resolve_user_from_session(DummySession(), "missing-token")

    assert exc.value.status_code == 401
    assert "Invalid session" in exc.value.detail


@pytest.mark.asyncio
async def test_logout_deletes_session(monkeypatch):
    deleted = {}

    async def fake_delete_session(_session, token):
        deleted["token"] = token

    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.delete_session", fake_delete_session)

    await AuthService.logout(DummySession(), "token-123")
    assert deleted["token"] == "token-123"
