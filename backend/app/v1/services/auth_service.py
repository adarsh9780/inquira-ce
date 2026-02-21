"""Authentication service with cookie-session helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.database import get_session as get_legacy_session, get_user_by_id as get_legacy_user_by_id
from ..models.user import User
from ..repositories.user_repository import UserRepository
from .security_service import generate_salt, hash_password, generate_session_token


class AuthService:
    """Business logic for registration, login, and session validation."""

    @staticmethod
    async def register_and_login(
        session: AsyncSession,
        username: str,
        password: str,
    ) -> tuple[str, str, str]:
        """Register user then create session token in one operation.

        Returns:
            tuple: (session_token, user_id, plan)
        """
        existing = await UserRepository.get_by_username(session, username)
        if existing is not None:
            raise HTTPException(status_code=400, detail="Username already exists")

        salt = generate_salt()
        password_hash = hash_password(password, salt)
        user = await UserRepository.create_user(session, username, password_hash, salt)

        session_token = generate_session_token()
        await UserRepository.create_session(session, session_token, user.id)
        await session.commit()
        return session_token, user.id, user.plan.value

    @staticmethod
    async def login(
        session: AsyncSession,
        username: str,
        password: str,
    ) -> tuple[str, str, str]:
        """Authenticate and create session token.

        Returns:
            tuple: (session_token, user_id, plan)
        """
        user = await UserRepository.get_by_username(session, username)
        if user is None:
            raise HTTPException(status_code=401, detail="Username does not exist")

        candidate = hash_password(password, user.salt)
        if candidate != user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        session_token = generate_session_token()
        await UserRepository.create_session(session, session_token, user.id)
        await session.commit()
        return session_token, user.id, user.plan.value

    @staticmethod
    async def resolve_user_from_session(
        session: AsyncSession,
        session_token: str,
    ):
        """Resolve authenticated user from session token and enforce TTL."""
        db_session = await UserRepository.get_session(session, session_token)
        if db_session is None:
            legacy_user = await AuthService._bridge_legacy_session(session, session_token)
            if legacy_user is None:
                raise HTTPException(status_code=401, detail="Invalid session")
            return legacy_user

        if UserRepository.is_expired(db_session):
            await UserRepository.delete_session(session, session_token)
            await session.commit()
            raise HTTPException(status_code=401, detail="Session expired")

        user = await UserRepository.get_by_id(session, db_session.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @staticmethod
    async def _bridge_legacy_session(
        session: AsyncSession,
        session_token: str,
    ):
        """Bridge legacy auth sessions into v1 session records on-demand."""
        legacy_session = await asyncio.to_thread(get_legacy_session, session_token)
        if legacy_session is None:
            return None

        created_at_raw = legacy_session.get("created_at")
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(str(created_at_raw).replace(" ", "T"))
                if datetime.now() - created_at > timedelta(hours=24):
                    return None
            except ValueError:
                return None

        legacy_user_id = legacy_session.get("user_id")
        if not legacy_user_id:
            return None

        legacy_user = await asyncio.to_thread(get_legacy_user_by_id, legacy_user_id)
        if legacy_user is None:
            return None

        user = await UserRepository.get_by_id(session, legacy_user["user_id"])
        if user is None:
            user_with_username = await UserRepository.get_by_username(session, legacy_user["username"])
            if user_with_username is not None and user_with_username.id != legacy_user["user_id"]:
                raise HTTPException(status_code=401, detail="Invalid session")

            user = User(
                id=legacy_user["user_id"],
                username=legacy_user["username"],
                password_hash=legacy_user.get("password_hash") or "legacy_sync",
                salt=legacy_user.get("salt") or "legacy_sync",
            )
            session.add(user)
            await session.flush()

        await UserRepository.create_session(session, session_token, user.id)
        await session.commit()
        return user
