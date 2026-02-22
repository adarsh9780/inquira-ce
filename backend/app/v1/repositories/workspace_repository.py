"""Repository methods for workspace persistence."""

from __future__ import annotations

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Workspace


class WorkspaceRepository:
    """Workspace DB access abstraction."""

    @staticmethod
    async def list_for_user(session: AsyncSession, user_id: str) -> list[Workspace]:
        """List all workspaces for a user."""
        result = await session.execute(
            select(Workspace).where(Workspace.user_id == user_id).order_by(Workspace.updated_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_for_user(session: AsyncSession, user_id: str) -> int:
        """Count user workspaces."""
        rows = await WorkspaceRepository.list_for_user(session, user_id)
        return len(rows)

    @staticmethod
    async def get_by_id(session: AsyncSession, workspace_id: str, user_id: str) -> Workspace | None:
        """Get workspace by id and user ownership."""
        result = await session.execute(
            select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name_normalized(
        session: AsyncSession,
        user_id: str,
        name_normalized: str,
    ) -> Workspace | None:
        """Fetch workspace by normalized name for uniqueness checks."""
        result = await session.execute(
            select(Workspace).where(
                Workspace.user_id == user_id,
                Workspace.name_normalized == name_normalized,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        session: AsyncSession,
        user_id: str,
        name: str,
        name_normalized: str,
        duckdb_path: str,
        is_active: int,
    ) -> Workspace:
        """Create workspace row."""
        workspace = Workspace(
            user_id=user_id,
            name=name,
            name_normalized=name_normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
        )
        session.add(workspace)
        await session.flush()
        return workspace

    @staticmethod
    async def deactivate_all_for_user(session: AsyncSession, user_id: str) -> None:
        """Mark all user workspaces inactive."""
        await session.execute(
            update(Workspace).where(Workspace.user_id == user_id).values(is_active=0)
        )

    @staticmethod
    async def delete(session: AsyncSession, workspace: Workspace) -> None:
        """Delete workspace row."""
        await session.delete(workspace)
