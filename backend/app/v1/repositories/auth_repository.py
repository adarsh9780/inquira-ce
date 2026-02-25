"""Auth/session repository contract for pluggable storage backends."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class AuthUserRecord:
    """Storage-agnostic authenticated user record."""

    id: str
    username: str
    password_hash: str
    salt: str
    plan: str


@dataclass(frozen=True)
class AuthSessionRecord:
    """Storage-agnostic auth session record."""

    session_token: str
    user_id: str
    created_at: datetime


class AuthRepository(Protocol):
    """Contract required by AuthService for auth/session operations."""

    async def get_by_username(self, username: str) -> AuthUserRecord | None: ...

    async def get_by_id(self, user_id: str) -> AuthUserRecord | None: ...

    async def create_user(self, username: str, password_hash: str, salt: str) -> AuthUserRecord: ...

    async def create_session(self, session_token: str, user_id: str) -> AuthSessionRecord: ...

    async def get_session(self, session_token: str) -> AuthSessionRecord | None: ...

    async def delete_session(self, session_token: str) -> None: ...
