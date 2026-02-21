"""Authentication service with cookie-session helpers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
            raise HTTPException(status_code=401, detail="Invalid session")

        if UserRepository.is_expired(db_session):
            await UserRepository.delete_session(session, session_token)
            await session.commit()
            raise HTTPException(status_code=401, detail="Session expired")

        user = await UserRepository.get_by_id(session, db_session.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user

    @staticmethod
    async def logout(
        session: AsyncSession,
        session_token: str,
    ) -> None:
        """Delete current v1 session token."""
        await UserRepository.delete_session(session, session_token)
        await session.commit()
