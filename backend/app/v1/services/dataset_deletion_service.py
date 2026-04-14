"""Asynchronous dataset physical-deletion service and background runner."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
                workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
                if workspace is not None:
                    duckdb_path = str(workspace.duckdb_path or "").strip()

            if duckdb_path:
                await asyncio.to_thread(
                    self._drop_workspace_table,
                    duckdb_path,
                    table_name,
                )

            async with AppDataSessionLocal() as session:
                job = await DatasetDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "completed"
                    job.error_message = None
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            async with AppDataSessionLocal() as session:
                job = await DatasetDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                await session.commit()

    @staticmethod
    def _drop_workspace_table(duckdb_path: str, table_name: str) -> None:
        """Drop one table from the workspace DuckDB file."""
        import duckdb

        db_path = Path(duckdb_path).expanduser()
        if not db_path.exists():
            return
        escaped_table = str(table_name).replace('"', '""')
        conn = duckdb.connect(str(db_path), read_only=False)
        try:
            conn.execute(f'DROP TABLE IF EXISTS "{escaped_table}"')
        finally:
            conn.close()
