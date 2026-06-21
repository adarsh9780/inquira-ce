"""Verify CE guest-first auth resolution behaves correctly."""

from __future__ import annotations

import pytest

from app.v1.api.deps import get_current_user


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
async def test_get_current_user_ignores_bearer_tokens_in_ce():
    """CE resolves every request to the local user without external auth."""
    user = await get_current_user("Bearer real-token")

    assert user.id == "local-user"
    assert user.username == "Local User"
    assert user.plan == "FREE"
    assert user.is_authenticated is False
    assert user.is_guest is True
    assert user.auth_provider == "local"
