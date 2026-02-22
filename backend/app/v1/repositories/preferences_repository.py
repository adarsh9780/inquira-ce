"""Repository methods for v1 user preferences."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserPreferences


class PreferencesRepository:
    """Persistence helpers for per-user preferences."""

    @staticmethod
    async def get_for_user(session: AsyncSession, user_id: str) -> UserPreferences | None:
        result = await session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(session: AsyncSession, user_id: str) -> UserPreferences:
        prefs = await PreferencesRepository.get_for_user(session, user_id)
        if prefs is not None:
            return prefs
        prefs = UserPreferences(user_id=user_id)
        session.add(prefs)
        await session.flush()
        return prefs
