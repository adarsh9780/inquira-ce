"""Repository methods for user and session persistence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserSession


class UserRepository:
    """Encapsulates user and session database operations."""

    @staticmethod
    async def get_by_username(session: AsyncSession, username: str) -> User | None:
        """Fetch user by username."""
        result = await session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: str) -> User | None:
        """Fetch user by id."""
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        username: str,
        password_hash: str,
        salt: str,
    ) -> User:
        """Create and persist a new user."""
        user = User(username=username, password_hash=password_hash, salt=salt)
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def create_session(session: AsyncSession, session_token: str, user_id: str) -> UserSession:
        """Create a new cookie-backed session."""
        db_session = UserSession(session_token=session_token, user_id=user_id)
        session.add(db_session)
        await session.flush()
        return db_session

    @staticmethod
    async def get_session(session: AsyncSession, session_token: str) -> UserSession | None:
        """Get a session by token."""
        result = await session.execute(
            select(UserSession).where(UserSession.session_token == session_token)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_session(session: AsyncSession, session_token: str) -> None:
        """Delete a session by token."""
        await session.execute(delete(UserSession).where(UserSession.session_token == session_token))

    @staticmethod
    def is_expired(db_session: UserSession, ttl_hours: int = 24) -> bool:
        """Check session TTL expiry."""
        created = db_session.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created > timedelta(hours=ttl_hours)
