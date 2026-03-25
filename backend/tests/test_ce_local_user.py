"""Verify CE local-user auth bypass works correctly."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.v1.api.deps import get_current_user


@pytest.mark.asyncio
async def test_get_current_user_returns_local_user_without_auth():
    """CE edition returns a fixed local user without any auth headers."""
    request = MagicMock()
    request.headers = {}

    user = await get_current_user(request)

    assert user.id == "local-user"
    assert user.username == "Local User"
    assert user.plan == "FREE"
    assert user.password_hash == ""
    assert user.salt == ""


@pytest.mark.asyncio
async def test_get_current_user_ignores_bearer_token():
    """CE edition ignores any auth headers — always returns local user."""
    request = MagicMock()
    request.headers = {"authorization": "Bearer some-fake-token"}

    user = await get_current_user(request)

    assert user.id == "local-user"
    assert user.username == "Local User"
    assert user.plan == "FREE"
