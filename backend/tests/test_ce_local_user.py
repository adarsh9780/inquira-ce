"""Verify CE guest-first auth resolution behaves correctly."""

from __future__ import annotations

import pytest

from app.v1.api.deps import get_current_user
from app.v1.repositories.auth_repository import AuthUserRecord


@pytest.mark.asyncio
async def test_get_current_user_returns_local_user_without_auth():
    """CE stays usable without auth by resolving to a guest local user."""
    user = await get_current_user(None)

    assert user.id == "local-user"
    assert user.username == "Local User"
    assert user.plan == "FREE"
    assert user.is_authenticated is False
    assert user.is_guest is True
    assert user.password_hash == ""
    assert user.salt == ""


@pytest.mark.asyncio
async def test_get_current_user_uses_supabase_resolution(monkeypatch):
    """Bearer-token auth delegates to the Supabase-backed resolver."""

    async def _fake_resolver(header):
        assert header == "Bearer real-token"
        return AuthUserRecord(
            id="user-123",
            username="Ada Lovelace",
            email="ada@example.com",
            password_hash="",
            salt="",
            plan="PRO",
            is_authenticated=True,
            is_guest=False,
            auth_provider="google",
        )

    monkeypatch.setattr("app.v1.api.deps.SupabaseAuthService.resolve_current_user", _fake_resolver)

    user = await get_current_user("Bearer real-token")

    assert user.id == "user-123"
    assert user.username == "Ada Lovelace"
    assert user.plan == "PRO"
    assert user.is_authenticated is True
    assert user.is_guest is False
