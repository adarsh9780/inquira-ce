"""Supabase-backed auth/session repository placeholder."""

from __future__ import annotations

from .auth_repository import AuthRepository, AuthSessionRecord, AuthUserRecord


class SupabaseAuthRepository(AuthRepository):
    """Placeholder provider for future Supabase auth/session migration."""

    def __init__(self, *_args, **_kwargs):
        pass

    async def get_by_username(self, username: str) -> AuthUserRecord | None:
        raise RuntimeError("Supabase auth provider is not implemented yet.")

    async def get_by_id(self, user_id: str) -> AuthUserRecord | None:
        raise RuntimeError("Supabase auth provider is not implemented yet.")

    async def create_user(self, username: str, password_hash: str, salt: str) -> AuthUserRecord:
        raise RuntimeError("Supabase auth provider is not implemented yet.")

    async def create_session(self, session_token: str, user_id: str) -> AuthSessionRecord:
        raise RuntimeError("Supabase auth provider is not implemented yet.")

    async def get_session(self, session_token: str) -> AuthSessionRecord | None:
        raise RuntimeError("Supabase auth provider is not implemented yet.")

    async def delete_session(self, session_token: str) -> None:
        raise RuntimeError("Supabase auth provider is not implemented yet.")
