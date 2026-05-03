"""Persistence operations for dataset ingestion jobs."""

from __future__ import annotations

import json

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDatasetIngestionJob


class DatasetIngestionRepository:
    """Repository for batch dataset ingestion job lifecycle."""

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
                WorkspaceDatasetIngestionJob.status.in_(("queued", "running")),
            )
            .order_by(desc(WorkspaceDatasetIngestionJob.created_at))
        )
        return list(result.scalars().all())
