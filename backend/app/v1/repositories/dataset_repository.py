"""Repository methods for workspace dataset metadata."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDataset


class DatasetRepository:
    """Workspace dataset metadata access."""

    @staticmethod
    async def get_latest_for_workspace(session: AsyncSession, workspace_id: str) -> WorkspaceDataset | None:
        """Return the most recently updated dataset in a workspace."""
        result = await session.execute(
            select(WorkspaceDataset)
            .where(WorkspaceDataset.workspace_id == workspace_id)
            .order_by(desc(WorkspaceDataset.updated_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
