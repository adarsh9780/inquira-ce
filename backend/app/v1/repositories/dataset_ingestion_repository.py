"""Persistence operations for dataset ingestion jobs."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDatasetIngestionJob


class DatasetIngestionRepository:
    """Repository for batch dataset ingestion job lifecycle."""

    ACTIVE_STATUSES = ("queued", "running")

    @staticmethod
    async def create_job(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        source_paths: list[str],
    ) -> WorkspaceDatasetIngestionJob:
        """Create a queued ingestion job with one item per source path."""
        items = [
            {
                "source_path": path,
                "status": "queued",
                "table_name": None,
                "row_count": None,
                "error_message": None,
            }
            for path in source_paths
        ]
        job = WorkspaceDatasetIngestionJob(
            owner_principal_id=principal_id,
            workspace_id=workspace_id,
            status="queued",
            total_count=len(items),
            completed_count=0,
            failed_count=0,
            items_json=json.dumps(items),
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def get_by_id(session: AsyncSession, job_id: str) -> WorkspaceDatasetIngestionJob | None:
        """Get one dataset ingestion job by id."""
        result = await session.execute(
            select(WorkspaceDatasetIngestionJob).where(WorkspaceDatasetIngestionJob.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_active_for_workspace(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ) -> list[WorkspaceDatasetIngestionJob]:
        """List active ingestion jobs for one workspace."""
        result = await session.execute(
            select(WorkspaceDatasetIngestionJob)
            .where(
                WorkspaceDatasetIngestionJob.owner_principal_id == principal_id,
                WorkspaceDatasetIngestionJob.workspace_id == workspace_id,
                WorkspaceDatasetIngestionJob.status.in_(DatasetIngestionRepository.ACTIVE_STATUSES),
            )
            .order_by(desc(WorkspaceDatasetIngestionJob.created_at))
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_pending_jobs(
        session: AsyncSession,
        *,
        limit: int = 100,
    ) -> list[WorkspaceDatasetIngestionJob]:
        result = await session.execute(
            select(WorkspaceDatasetIngestionJob)
            .where(WorkspaceDatasetIngestionJob.status.in_(DatasetIngestionRepository.ACTIVE_STATUSES))
            .order_by(WorkspaceDatasetIngestionJob.created_at.asc(), WorkspaceDatasetIngestionJob.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def reset_claims_for_active_jobs(session: AsyncSession) -> None:
        await session.execute(
            update(WorkspaceDatasetIngestionJob)
            .execution_options(synchronize_session=False)
            .where(WorkspaceDatasetIngestionJob.status.in_(DatasetIngestionRepository.ACTIVE_STATUSES))
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
    ) -> WorkspaceDatasetIngestionJob | None:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        result = await session.execute(
            update(WorkspaceDatasetIngestionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetIngestionJob.id == job_id,
                WorkspaceDatasetIngestionJob.status.in_(DatasetIngestionRepository.ACTIVE_STATUSES),
                or_(
                    WorkspaceDatasetIngestionJob.claimed_by.is_(None),
                    WorkspaceDatasetIngestionJob.claimed_by == worker_id,
                    WorkspaceDatasetIngestionJob.lease_expires_at.is_(None),
                    WorkspaceDatasetIngestionJob.lease_expires_at <= now,
                ),
            )
            .values(
                status="running",
                claimed_by=worker_id,
                lease_expires_at=lease_until,
                last_heartbeat_at=now,
                attempt_count=WorkspaceDatasetIngestionJob.attempt_count + 1,
            )
        )
        if not result.rowcount:
            await session.rollback()
            return None
        await session.commit()
        return await DatasetIngestionRepository.get_by_id(session, job_id)

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
            update(WorkspaceDatasetIngestionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetIngestionJob.id == job_id,
                WorkspaceDatasetIngestionJob.claimed_by == worker_id,
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
            update(WorkspaceDatasetIngestionJob)
            .execution_options(synchronize_session=False)
            .where(
                WorkspaceDatasetIngestionJob.id == job_id,
                WorkspaceDatasetIngestionJob.claimed_by == worker_id,
            )
            .values(claimed_by=None, lease_expires_at=None, last_heartbeat_at=None)
        )
        await session.commit()
