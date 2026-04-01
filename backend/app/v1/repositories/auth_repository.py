"""Storage-agnostic authenticated user payload."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUserRecord:
    """Storage-agnostic authenticated user record."""

    id: str
    username: str
    email: str
    password_hash: str
    salt: str
    plan: str
    is_authenticated: bool = True
    is_guest: bool = False
    auth_provider: str = "local"
