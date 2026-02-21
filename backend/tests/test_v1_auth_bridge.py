from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.v1.services.auth_service import AuthService


class DummySession:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_resolve_user_from_session_bridges_legacy_session(monkeypatch):
    dummy_session = DummySession()

    async def fake_get_session(_session, _token):
        return None

    async def fake_get_by_id(_session, _user_id):
        return None

    async def fake_get_by_username(_session, _username):
        return None

    async def fake_create_session(_session, _token, _user_id):
        return None

    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.get_session", fake_get_session)
    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.get_by_id", fake_get_by_id)
    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.get_by_username", fake_get_by_username)
    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.create_session", fake_create_session)
    monkeypatch.setattr(
        "app.v1.services.auth_service.get_legacy_session",
        lambda _token: {"user_id": "legacy-user-1", "created_at": datetime.now().isoformat()},
    )
    monkeypatch.setattr(
        "app.v1.services.auth_service.get_legacy_user_by_id",
        lambda _user_id: {
            "user_id": "legacy-user-1",
            "username": "legacy",
            "password_hash": "hash",
            "salt": "salt",
        },
    )

    user = await AuthService.resolve_user_from_session(dummy_session, "token-1")

    assert user.id == "legacy-user-1"
    assert user.username == "legacy"
    assert dummy_session.flushed is True
    assert dummy_session.committed is True


@pytest.mark.asyncio
async def test_resolve_user_from_session_rejects_expired_legacy_session(monkeypatch):
    dummy_session = DummySession()

    async def fake_get_session(_session, _token):
        return None

    monkeypatch.setattr("app.v1.services.auth_service.UserRepository.get_session", fake_get_session)
    monkeypatch.setattr(
        "app.v1.services.auth_service.get_legacy_session",
        lambda _token: {
            "user_id": "legacy-user-1",
            "created_at": (datetime.now() - timedelta(hours=25)).isoformat(),
        },
    )

    with pytest.raises(HTTPException) as exc:
        await AuthService.resolve_user_from_session(dummy_session, "token-1")

    assert exc.value.status_code == 401
