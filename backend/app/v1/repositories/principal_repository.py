"""Repository methods for appdata principal persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Principal


class PrincipalRepository:
    """Persistence helpers for appdata identity principals."""

    @staticmethod
    async def get_by_id(session: AsyncSession, principal_id: str) -> Principal | None:
        result = await session.execute(
            select(Principal).where(Principal.id == principal_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        principal_id: str,
        username: str,
        plan: str,
    ) -> Principal:
        principal = await PrincipalRepository.get_by_id(session, principal_id)
        normalized_plan = str(plan or "FREE")
        if principal is not None:
            changed = False
            if principal.username_cached != username:
                principal.username_cached = username
                changed = True
            if principal.plan_cached != normalized_plan:
                principal.plan_cached = normalized_plan
                changed = True
            if changed:
                await session.flush()
            return principal

        principal = Principal(
            id=principal_id,
            username_cached=username,
            plan_cached=normalized_plan,
        )
        session.add(principal)
        await session.flush()
        return principal
