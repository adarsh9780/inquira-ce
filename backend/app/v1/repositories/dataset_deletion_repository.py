"""Persistence operations for dataset deletion jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDatasetDeletionJob


class DatasetDeletionRepository:
    """Repository for dataset deletion job lifecycle."""

    ACTIVE_STATUSES = ("queued", "running")

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
                WorkspaceDatasetDeletionJob.status.in_(DatasetDeletionRepository.ACTIVE_STATUSES),
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
                WorkspaceDatasetDeletionJob.status.in_(DatasetDeletionRepository.ACTIVE_STATUSES),
            )
            .order_by(desc(WorkspaceDatasetDeletionJob.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_pending_jobs(session: AsyncSession, *, limit: int = 100) -> list[WorkspaceDatasetDeletionJob]:
        result = await session.execute(
            select(WorkspaceDatasetDeletionJob)
            .where(WorkspaceDatasetDeletionJob.status.in_(DatasetDeletionRepository.ACTIVE_STATUSES))
            .order_by(WorkspaceDatasetDeletionJob.created_at.asc(), WorkspaceDatasetDeletionJob.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def reset_claims_for_active_jobs(session: AsyncSession) -> None:
        await session.execute(
            update(WorkspaceDatasetDeletionJob)
            .execution_options(synchronize_session=False)
            .where(WorkspaceDatasetDeletionJob.status.in_(DatasetDeletionRepository.ACTIVE_STATUSES))
            .values(claimed_by=None, lease_expires_at=None, last_heartbeat_at=None)
        )
        await session.commit()

    @staticmethod
    async def claim_job(
        session: AsyncSession,
        *,
        job_id: str,
        worker_id: str,
        lease_seconds: int,
    ) -> WorkspaceDatasetDeletionJob | None:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        result = await session.execute(
            update(WorkspaceDatasetDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetDeletionJob.id == job_id,
                WorkspaceDatasetDeletionJob.status.in_(DatasetDeletionRepository.ACTIVE_STATUSES),
                or_(
                    WorkspaceDatasetDeletionJob.claimed_by.is_(None),
                    WorkspaceDatasetDeletionJob.claimed_by == worker_id,
                    WorkspaceDatasetDeletionJob.lease_expires_at.is_(None),
                    WorkspaceDatasetDeletionJob.lease_expires_at <= now,
                ),
            )
            .values(
                status="running",
                claimed_by=worker_id,
                lease_expires_at=lease_until,
                last_heartbeat_at=now,
                attempt_count=WorkspaceDatasetDeletionJob.attempt_count + 1,
            )
        )
        if not result.rowcount:
            await session.rollback()
            return None
        await session.commit()
        return await DatasetDeletionRepository.get_by_id(session, job_id)

    @staticmethod
    async def heartbeat_job(
        session: AsyncSession,
        *,
        job_id: str,
        worker_id: str,
        lease_seconds: int,
    ) -> None:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        await session.execute(
            update(WorkspaceDatasetDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetDeletionJob.id == job_id,
                WorkspaceDatasetDeletionJob.claimed_by == worker_id,
            )
            .values(last_heartbeat_at=now, lease_expires_at=lease_until)
        )
        await session.commit()

    @staticmethod
    async def release_claim(
        session: AsyncSession,
        *,
        job_id: str,
        worker_id: str,
    ) -> None:
        await session.execute(
            update(WorkspaceDatasetDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetDeletionJob.id == job_id,
                WorkspaceDatasetDeletionJob.claimed_by == worker_id,
            )
            .values(claimed_by=None, lease_expires_at=None, last_heartbeat_at=None)
        )
        await session.commit()
