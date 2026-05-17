"""Asynchronous dataset physical-deletion service and background runner."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...data_access.coordinator import LeaseKinds, ResourceLeaseCoordinator
from ...data_access.workspace_db import WorkspaceOfflineAdapter
from ...services.code_executor import reset_workspace_kernel
from ..db.session import AppDataSessionLocal
from ..repositories.dataset_deletion_repository import DatasetDeletionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .dataset_service import DatasetService


class DatasetDeletionService:
    """Manage dataset delete-job lifecycle."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def enqueue_dataset_deletion(
        self,
        session: AsyncSession,
        user,
        workspace_id: str,
        table_name: str,
    ):
        """Create or reuse delete job, remove metadata immediately, then schedule physical cleanup."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        normalized_table = str(table_name or "").strip()
        if not normalized_table:
            raise HTTPException(status_code=400, detail="Dataset table name is required")

        active_job = await DatasetDeletionRepository.get_active_for_table(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
            table_name=normalized_table,
        )
        if active_job is not None:
            return active_job

        await DatasetService.remove_dataset(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
            table_name=normalized_table,
        )

        job = await DatasetDeletionRepository.create_job(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
            table_name=normalized_table,
        )
        await session.commit()
        await session.refresh(job)

        await self._schedule_job(
            job_id=job.id,
            workspace_id=workspace_id,
            principal_id=user.id,
            table_name=normalized_table,
        )
        return job

    async def get_job_for_principal(
        self,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        job_id: str,
    ):
        """Get one dataset delete job and enforce ownership/workspace scope."""
        job = await DatasetDeletionRepository.get_by_id(session, job_id)
        if (
            job is None
            or job.owner_principal_id != principal_id
            or str(job.workspace_id) != str(workspace_id)
        ):
            raise HTTPException(status_code=404, detail="Dataset deletion job not found")
        return job

    async def list_active_jobs_for_workspace(
        self,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ):
        """List active dataset delete jobs for one workspace."""
        return await DatasetDeletionRepository.list_active_for_workspace(
            session=session,
            principal_id=principal_id,
            workspace_id=workspace_id,
        )

    async def shutdown(self) -> None:
        """Cancel all active background deletion tasks."""
        async with self._lock:
            for task in self._tasks.values():
                task.cancel()
            self._tasks.clear()

    async def _schedule_job(
        self,
        *,
        job_id: str,
        workspace_id: str,
        principal_id: str,
        table_name: str,
    ) -> None:
        """Schedule one background physical cleanup task."""
        async with self._lock:
            if job_id in self._tasks and not self._tasks[job_id].done():
                return
            task = asyncio.create_task(
                self._run_delete_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    table_name=table_name,
                )
            )
            self._tasks[job_id] = task
            task.add_done_callback(lambda _task: self._tasks.pop(job_id, None))

    async def _run_delete_job(
        self,
        *,
        job_id: str,
        workspace_id: str,
        principal_id: str,
        table_name: str,
    ) -> None:
        """Execute delete job: release kernel, drop table from workspace DB, update status."""
        maintenance_owner_token = f"dataset-delete:{job_id}:{uuid.uuid4()}"
        async with AppDataSessionLocal() as session:
            job = await DatasetDeletionRepository.get_by_id(session, job_id)
            if job is None:
                return
            job.status = "running"
            job.error_message = None
            await session.commit()

        try:
            try:
                await reset_workspace_kernel(workspace_id)
            except Exception:
                # Best-effort unlock. Drop can still succeed without this.
                pass

            duckdb_path = ""
            async with AppDataSessionLocal() as session:
                coordinator = ResourceLeaseCoordinator()
                await coordinator.acquire_workspace_maintenance_lease(
                    session,
                    workspace_id=workspace_id,
                    owner_token=maintenance_owner_token,
                    metadata={"job_id": job_id, "source": "dataset_deletion"},
                )
                await session.commit()
                workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
                if workspace is not None:
                    duckdb_path = str(workspace.duckdb_path or "").strip()
                if duckdb_path:
                    await WorkspaceOfflineAdapter(
                        session=session,
                        owner_token=maintenance_owner_token,
                        coordinator=coordinator,
                    ).drop_table(
                        workspace_id=workspace_id,
                        workspace_duckdb_path=duckdb_path,
                        table_name=table_name,
                    )
                await coordinator.release_lease(
                    session,
                    resource_key=workspace_id,
                    lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
                    owner_token=maintenance_owner_token,
                )
                await session.commit()

            async with AppDataSessionLocal() as session:
                job = await DatasetDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "completed"
                    job.error_message = None
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            async with AppDataSessionLocal() as session:
                await ResourceLeaseCoordinator().release_lease(
                    session,
                    resource_key=workspace_id,
                    lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
                    owner_token=maintenance_owner_token,
                )
                job = await DatasetDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                await session.commit()
