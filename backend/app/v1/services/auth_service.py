"""Authentication service with cookie-session helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.auth_repository import AuthRepository, AuthSessionRecord
from ..repositories.auth_repository_factory import get_auth_repository
from ..core.settings import settings
from ..repositories.auth_repository import AuthUserRecord
from .security_service import (
    generate_salt,
    generate_session_token,
    hash_password,
    verify_password,
)


class AuthService:
    """Business logic for registration, login, and session validation."""

    @staticmethod
    def _repo(session: AsyncSession, auth_repository: AuthRepository | None = None) -> AuthRepository:
        if auth_repository is not None:
            return auth_repository
        return get_auth_repository(session)

    @staticmethod
    def _is_expired(db_session: AuthSessionRecord, ttl_hours: int = 24) -> bool:
        created = db_session.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created > timedelta(hours=ttl_hours)

    @staticmethod
    async def register_and_login(
        session: AsyncSession,
        username: str,
        password: str,
        auth_repository: AuthRepository | None = None,
    ) -> tuple[str, str, str]:
        """Register user then create session token in one operation.

        Returns:
            tuple: (session_token, user_id, plan)
        """
        repo = AuthService._repo(session, auth_repository)
        existing = await repo.get_by_username(username)
        if existing is not None:
            raise HTTPException(status_code=400, detail="Username already exists")

        salt = generate_salt()
        password_hash = hash_password(password, salt)
        user = await repo.create_user(username, password_hash, salt)

        session_token = generate_session_token()
        await repo.create_session(session_token, user.id)
        await session.commit()
        return session_token, user.id, user.plan

    @staticmethod
    async def login(
        session: AsyncSession,
        username: str,
        password: str,
        auth_repository: AuthRepository | None = None,
    ) -> tuple[str, str, str]:
        """Authenticate and create session token.

        Returns:
            tuple: (session_token, user_id, plan)
        """
        repo = AuthService._repo(session, auth_repository)
        user = await repo.get_by_username(username)
        if user is None:
            raise HTTPException(status_code=401, detail="Username does not exist")

        if not verify_password(password, user.salt, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        session_token = generate_session_token()
        await repo.create_session(session_token, user.id)
        await session.commit()
        return session_token, user.id, user.plan

    @staticmethod
    async def resolve_user_from_session(
        session: AsyncSession,
        session_token: str,
        auth_repository: AuthRepository | None = None,
    ):
        """Resolve authenticated user from session token and enforce TTL."""
        repo = AuthService._repo(session, auth_repository)
        db_session = await repo.get_session(session_token)
        if db_session is None:
            raise HTTPException(status_code=401, detail="Invalid session")

        if AuthService._is_expired(db_session):
            await repo.delete_session(session_token)
            await session.commit()
            raise HTTPException(status_code=401, detail="Session expired")

        user = await repo.get_by_id(db_session.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @staticmethod
    async def logout(
        session: AsyncSession,
        session_token: str,
        auth_repository: AuthRepository | None = None,
    ) -> None:
        """Delete current v1 session token."""
        repo = AuthService._repo(session, auth_repository)
        await repo.delete_session(session_token)
        await session.commit()

    @staticmethod
    async def resolve_supabase_user(access_token: str) -> AuthUserRecord:
        """Resolve a user profile from a Supabase bearer token."""
        token = str(access_token or "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing bearer token")

        if not settings.supabase_url or not settings.supabase_secret_key:
            raise HTTPException(
                status_code=500,
                detail="Supabase auth is not configured on the backend.",
            )

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": settings.supabase_secret_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            ) from exc

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        if response.status_code >= 400:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            )

        payload = response.json()
        metadata = payload.get("user_metadata") or {}
        app_metadata = payload.get("app_metadata") or {}
        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            raise HTTPException(status_code=401, detail="Supabase user payload missing id")

        username = (
            str(payload.get("email") or "").strip()
            or str(payload.get("phone") or "").strip()
            or str(metadata.get("full_name") or "").strip()
            or user_id
        )
        plan = str(app_metadata.get("plan") or "FREE").strip() or "FREE"

        return AuthUserRecord(
            id=user_id,
            username=username,
            password_hash="",
            salt="",
            plan=plan.upper(),
        )
