"""Persistence operations for workspace deletion jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDeletionJob


class WorkspaceDeletionRepository:
    """Repository for workspace deletion job lifecycle."""

    ACTIVE_STATUSES = ("queued", "running")

    @staticmethod
    async def create_job(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ) -> WorkspaceDeletionJob:
        """Create a new queued deletion job."""
        job = WorkspaceDeletionJob(
            owner_principal_id=principal_id,
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
        principal_id: str,
        workspace_id: str,
    ) -> WorkspaceDeletionJob | None:
        """Get an active (queued/running) deletion job for a workspace."""
        result = await session.execute(
            select(WorkspaceDeletionJob)
            .where(
                WorkspaceDeletionJob.owner_principal_id == principal_id,
                WorkspaceDeletionJob.workspace_id == workspace_id,
                WorkspaceDeletionJob.status.in_(WorkspaceDeletionRepository.ACTIVE_STATUSES),
            )
            .order_by(desc(WorkspaceDeletionJob.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active_for_principal(
        session: AsyncSession,
        principal_id: str,
    ) -> list[WorkspaceDeletionJob]:
        """List active deletion jobs for the user."""
        result = await session.execute(
            select(WorkspaceDeletionJob)
            .where(
                WorkspaceDeletionJob.owner_principal_id == principal_id,
                WorkspaceDeletionJob.status.in_(WorkspaceDeletionRepository.ACTIVE_STATUSES),
            )
            .order_by(desc(WorkspaceDeletionJob.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_pending_jobs(session: AsyncSession, *, limit: int = 100) -> list[WorkspaceDeletionJob]:
        result = await session.execute(
            select(WorkspaceDeletionJob)
            .where(WorkspaceDeletionJob.status.in_(WorkspaceDeletionRepository.ACTIVE_STATUSES))
            .order_by(WorkspaceDeletionJob.created_at.asc(), WorkspaceDeletionJob.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def reset_claims_for_active_jobs(session: AsyncSession) -> None:
        await session.execute(
            update(WorkspaceDeletionJob)
            .execution_options(synchronize_session=False)
            .where(WorkspaceDeletionJob.status.in_(WorkspaceDeletionRepository.ACTIVE_STATUSES))
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
    ) -> WorkspaceDeletionJob | None:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        result = await session.execute(
            update(WorkspaceDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDeletionJob.id == job_id,
                WorkspaceDeletionJob.status.in_(WorkspaceDeletionRepository.ACTIVE_STATUSES),
                or_(
                    WorkspaceDeletionJob.claimed_by.is_(None),
                    WorkspaceDeletionJob.claimed_by == worker_id,
                    WorkspaceDeletionJob.lease_expires_at.is_(None),
                    WorkspaceDeletionJob.lease_expires_at <= now,
                ),
            )
            .values(
                status="running",
                claimed_by=worker_id,
                lease_expires_at=lease_until,
                last_heartbeat_at=now,
                attempt_count=WorkspaceDeletionJob.attempt_count + 1,
            )
            .returning(WorkspaceDeletionJob.id)
        )
        if result.scalar_one_or_none() is None:
            await session.rollback()
            return None
        await session.commit()
        return await WorkspaceDeletionRepository.get_by_id(session, job_id)

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
            update(WorkspaceDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDeletionJob.id == job_id,
                WorkspaceDeletionJob.claimed_by == worker_id,
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
            update(WorkspaceDeletionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDeletionJob.id == job_id,
                WorkspaceDeletionJob.claimed_by == worker_id,
            )
            .values(claimed_by=None, lease_expires_at=None, last_heartbeat_at=None)
        )
        await session.commit()
