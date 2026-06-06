"""Asynchronous workspace deletion service and background runner."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AppDataSessionLocal
from ..repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .workspace_maintenance_service import WorkspaceMaintenanceService
from .workspace_storage_service import WorkspaceStorageService
from .workspace_service import WorkspaceService


class WorkspaceDeletionService:
    """Manage delete-job lifecycle for workspaces."""

    CLAIM_LEASE_SECONDS = 300

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def enqueue_workspace_deletion(
        self,
        session: AsyncSession,
        user,
        workspace_id: str,
        langgraph_manager,
    ):
        """Create or reuse delete job, then schedule async cleanup."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        active_job = await WorkspaceDeletionRepository.get_active_for_workspace(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
        )
        if active_job is not None:
            return active_job

        job = await WorkspaceDeletionRepository.create_job(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
        )
        await session.commit()
        await session.refresh(job)

        await self._schedule_job(
            job_id=job.id,
            workspace_id=workspace_id,
            principal_id=user.id,
            username=user.id,
            langgraph_manager=langgraph_manager,
        )
        return job

    async def get_job_for_principal(
        self,
        session: AsyncSession,
        principal_id: str,
        job_id: str,
    ):
        """Get one delete job and enforce ownership."""
        job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
        if job is None or job.owner_principal_id != principal_id:
            raise HTTPException(status_code=404, detail="Deletion job not found")
        return job

    async def list_active_jobs_for_principal(self, session: AsyncSession, principal_id: str):
        """List active delete jobs for workspace dropdown status."""
        return await WorkspaceDeletionRepository.list_active_for_principal(session, principal_id)

    async def shutdown(self) -> None:
        """Cancel all active background deletion tasks."""
        async with self._lock:
            for task in self._tasks.values():
                task.cancel()
            self._tasks.clear()

    async def resume_pending_jobs(self, *, langgraph_manager) -> None:
        """Resume queued/running deletion jobs after backend restart."""
        async with AppDataSessionLocal() as session:
            await WorkspaceDeletionRepository.reset_claims_for_active_jobs(session)
            jobs = await WorkspaceDeletionRepository.list_pending_jobs(session)
            for job in jobs:
                username = str(job.owner_principal_id)
                await self._schedule_job(
                    job_id=str(job.id),
                    workspace_id=str(job.workspace_id),
                    principal_id=str(job.owner_principal_id),
                    username=username,
                    langgraph_manager=langgraph_manager,
                )

    async def _schedule_job(
        self,
        job_id: str,
        workspace_id: str,
        principal_id: str,
        username: str,
        langgraph_manager,
    ) -> None:
        """Schedule one background cleanup task."""
        async with self._lock:
            if job_id in self._tasks and not self._tasks[job_id].done():
                return
            task = asyncio.create_task(
                self._run_delete_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    username=username,
                    langgraph_manager=langgraph_manager,
                )
            )
            self._tasks[job_id] = task
            task.add_done_callback(lambda _task: self._tasks.pop(job_id, None))

    async def _run_delete_job(
        self,
        job_id: str,
        workspace_id: str,
        principal_id: str,
        username: str,
        langgraph_manager,
    ) -> None:
        """Execute delete job: close graph, delete files, remove DB row, update status."""
        maintenance_owner_token = f"workspace-delete:{job_id}:{uuid.uuid4()}"
        worker_id = f"workspace-delete:{job_id}:{uuid.uuid4()}"
        async with AppDataSessionLocal() as session:
            job = await WorkspaceDeletionRepository.claim_job(
                session,
                job_id=job_id,
                worker_id=worker_id,
                lease_seconds=self.CLAIM_LEASE_SECONDS,
            )
            if job is None:
                return
            job.error_message = None
            await session.commit()

        try:
            await self._heartbeat(job_id=job_id, worker_id=worker_id)
            await langgraph_manager.close_workspace(workspace_id)
            await WorkspaceMaintenanceService.drain_runtime(
                workspace_id=workspace_id,
                user_id=str(principal_id),
            )
            await self._heartbeat(job_id=job_id, worker_id=worker_id)
            async with AppDataSessionLocal() as session:
                await WorkspaceMaintenanceService.acquire_lease_or_raise(
                    session,
                    workspace_id=workspace_id,
                    owner_token=maintenance_owner_token,
                    requested_operation="workspace_deletion",
                    metadata={"job_id": job_id, "source": "workspace_deletion"},
                )
            try:
                await WorkspaceStorageService.hard_delete_workspace(username, workspace_id)
            finally:
                async with AppDataSessionLocal() as session:
                    await WorkspaceMaintenanceService.release_lease(
                        session,
                        workspace_id=workspace_id,
                        owner_token=maintenance_owner_token,
                    )

            async with AppDataSessionLocal() as session:
                workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
                was_active = bool(getattr(workspace, "is_active", 0)) if workspace is not None else False
                if workspace is not None:
                    await WorkspaceRepository.delete(session, workspace)

                remaining = await WorkspaceRepository.list_for_principal(session, principal_id)
                next_workspace_id = str(remaining[0].id) if was_active and remaining else None
                if was_active or next_workspace_id is None:
                    await WorkspaceService._set_active_workspace_atomic(
                        session=session,
                        principal_id=str(principal_id),
                        workspace_id=next_workspace_id,
                    )

                job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "completed"
                    job.claimed_by = None
                    job.lease_expires_at = None
                    job.last_heartbeat_at = None
                    job.error_message = None

                await session.commit()
        except Exception as exc:  # noqa: BLE001
            async with AppDataSessionLocal() as session:
                await WorkspaceMaintenanceService.release_lease(
                    session,
                    workspace_id=workspace_id,
                    owner_token=maintenance_owner_token,
                )
                job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "failed"
                    job.claimed_by = None
                    job.lease_expires_at = None
                    job.last_heartbeat_at = None
                    raw_detail = getattr(exc, "detail", exc)
                    job.error_message = (
                        json.dumps(raw_detail, default=str) if isinstance(raw_detail, dict) else str(raw_detail)
                    )[:1000]
                await session.commit()

    async def _heartbeat(self, *, job_id: str, worker_id: str) -> None:
        async with AppDataSessionLocal() as session:
            await WorkspaceDeletionRepository.heartbeat_job(
                session,
                job_id=job_id,
                worker_id=worker_id,
                lease_seconds=self.CLAIM_LEASE_SECONDS,
            )
