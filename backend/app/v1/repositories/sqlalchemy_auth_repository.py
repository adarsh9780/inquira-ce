"""SQLAlchemy-backed auth/session repository implementation."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .auth_repository import AuthRepository, AuthSessionRecord, AuthUserRecord
from .user_repository import UserRepository


class SqlAlchemyAuthRepository(AuthRepository):
    """Auth repository using v1 SQLAlchemy ORM tables."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_username(self, username: str) -> AuthUserRecord | None:
        user = await UserRepository.get_by_username(self._session, username)
        if user is None:
            return None
        return AuthUserRecord(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            salt=user.salt,
            plan=user.plan.value,
        )

    async def get_by_id(self, user_id: str) -> AuthUserRecord | None:
        user = await UserRepository.get_by_id(self._session, user_id)
        if user is None:
            return None
        return AuthUserRecord(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            salt=user.salt,
            plan=user.plan.value,
        )

    async def create_user(self, username: str, password_hash: str, salt: str) -> AuthUserRecord:
        user = await UserRepository.create_user(self._session, username, password_hash, salt)
        return AuthUserRecord(
            id=user.id,
            username=user.username,
            password_hash=user.password_hash,
            salt=user.salt,
            plan=user.plan.value,
        )

    async def create_session(self, session_token: str, user_id: str) -> AuthSessionRecord:
        row = await UserRepository.create_session(self._session, session_token, user_id)
        return AuthSessionRecord(
            session_token=row.session_token,
            user_id=row.user_id,
            created_at=row.created_at,
        )

    async def get_session(self, session_token: str) -> AuthSessionRecord | None:
        row = await UserRepository.get_session(self._session, session_token)
        if row is None:
            return None
        return AuthSessionRecord(
            session_token=row.session_token,
            user_id=row.user_id,
            created_at=row.created_at,
        )

    async def delete_session(self, session_token: str) -> None:
        await UserRepository.delete_session(self._session, session_token)
