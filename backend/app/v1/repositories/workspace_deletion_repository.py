"""Persistence operations for workspace deletion jobs."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDeletionJob


class WorkspaceDeletionRepository:
    """Repository for workspace deletion job lifecycle."""

    @staticmethod
    async def create_job(session: AsyncSession, user_id: str, workspace_id: str) -> WorkspaceDeletionJob:
        """Create a new queued deletion job."""
        job = WorkspaceDeletionJob(
            user_id=user_id,
            workspace_id=workspace_id,
            status="queued",
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def get_by_id(session: AsyncSession, job_id: str) -> WorkspaceDeletionJob | None:
        """Get one deletion job by id."""
        result = await session.execute(
            select(WorkspaceDeletionJob).where(WorkspaceDeletionJob.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_for_workspace(
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
    ) -> WorkspaceDeletionJob | None:
        """Get an active (queued/running) deletion job for a workspace."""
        result = await session.execute(
            select(WorkspaceDeletionJob)
            .where(
                WorkspaceDeletionJob.user_id == user_id,
                WorkspaceDeletionJob.workspace_id == workspace_id,
                WorkspaceDeletionJob.status.in_(("queued", "running")),
            )
            .order_by(desc(WorkspaceDeletionJob.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active_for_user(session: AsyncSession, user_id: str) -> list[WorkspaceDeletionJob]:
        """List active deletion jobs for the user."""
        result = await session.execute(
            select(WorkspaceDeletionJob)
            .where(
                WorkspaceDeletionJob.user_id == user_id,
                WorkspaceDeletionJob.status.in_(("queued", "running")),
            )
            .order_by(desc(WorkspaceDeletionJob.created_at))
        )
        return list(result.scalars().all())
