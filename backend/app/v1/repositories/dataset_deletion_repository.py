"""Persistence operations for dataset deletion jobs."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDatasetDeletionJob


class DatasetDeletionRepository:
    """Repository for dataset deletion job lifecycle."""

    @staticmethod
    async def create_job(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        table_name: str,
    ) -> WorkspaceDatasetDeletionJob:
        """Create a new queued dataset deletion job."""
        job = WorkspaceDatasetDeletionJob(
            owner_principal_id=principal_id,
            workspace_id=workspace_id,
            table_name=table_name,
            status="queued",
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def get_by_id(session: AsyncSession, job_id: str) -> WorkspaceDatasetDeletionJob | None:
        """Get one dataset deletion job by id."""
        result = await session.execute(
            select(WorkspaceDatasetDeletionJob).where(WorkspaceDatasetDeletionJob.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_for_table(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        table_name: str,
    ) -> WorkspaceDatasetDeletionJob | None:
        """Get an active (queued/running) deletion job for one dataset table."""
        result = await session.execute(
            select(WorkspaceDatasetDeletionJob)
            .where(
                WorkspaceDatasetDeletionJob.owner_principal_id == principal_id,
                WorkspaceDatasetDeletionJob.workspace_id == workspace_id,
                WorkspaceDatasetDeletionJob.table_name == table_name,
                WorkspaceDatasetDeletionJob.status.in_(("queued", "running")),
            )
            .order_by(desc(WorkspaceDatasetDeletionJob.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active_for_workspace(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ) -> list[WorkspaceDatasetDeletionJob]:
        """List active dataset deletion jobs for one workspace."""
        result = await session.execute(
            select(WorkspaceDatasetDeletionJob)
            .where(
                WorkspaceDatasetDeletionJob.owner_principal_id == principal_id,
                WorkspaceDatasetDeletionJob.workspace_id == workspace_id,
                WorkspaceDatasetDeletionJob.status.in_(("queued", "running")),
            )
            .order_by(desc(WorkspaceDatasetDeletionJob.created_at))
        )
        return list(result.scalars().all())
