"""Factory for selecting auth repository provider by runtime settings."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.settings import settings
from .auth_repository import AuthRepository
from .sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from .supabase_auth_repository import SupabaseAuthRepository


def get_auth_repository(session: AsyncSession) -> AuthRepository:
    """Return configured auth/session repository implementation."""
    provider = settings.auth_provider
    if provider == "sqlite":
        return SqlAlchemyAuthRepository(session)
    if provider == "supabase":
        return SupabaseAuthRepository()
    raise RuntimeError(f"Unsupported INQUIRA_AUTH_PROVIDER value: {provider}")
