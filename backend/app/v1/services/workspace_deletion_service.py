"""Asynchronous workspace deletion service and background runner."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import SessionLocal
from ..repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .workspace_storage_service import WorkspaceStorageService


class WorkspaceDeletionService:
    """Manage delete-job lifecycle for workspaces."""

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
            user_id=user.id,
            workspace_id=workspace_id,
        )
        if active_job is not None:
            return active_job

        job = await WorkspaceDeletionRepository.create_job(
            session=session,
            user_id=user.id,
            workspace_id=workspace_id,
        )
        await session.commit()
        await session.refresh(job)

        await self._schedule_job(
            job_id=job.id,
            workspace_id=workspace_id,
            user_id=user.id,
            username=user.username,
            langgraph_manager=langgraph_manager,
        )
        return job

    async def get_job_for_user(
        self,
        session: AsyncSession,
        user_id: str,
        job_id: str,
    ):
        """Get one delete job and enforce ownership."""
        job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
        if job is None or job.user_id != user_id:
            raise HTTPException(status_code=404, detail="Deletion job not found")
        return job

    async def list_active_jobs_for_user(self, session: AsyncSession, user_id: str):
        """List active delete jobs for workspace dropdown status."""
        return await WorkspaceDeletionRepository.list_active_for_user(session, user_id)

    async def shutdown(self) -> None:
        """Cancel all active background deletion tasks."""
        async with self._lock:
            for task in self._tasks.values():
                task.cancel()
            self._tasks.clear()

    async def _schedule_job(
        self,
        job_id: str,
        workspace_id: str,
        user_id: str,
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
                    user_id=user_id,
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
        user_id: str,
        username: str,
        langgraph_manager,
    ) -> None:
        """Execute delete job: close graph, delete files, remove DB row, update status."""
        async with SessionLocal() as session:
            job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
            if job is None:
                return
            job.status = "running"
            job.error_message = None
            await session.commit()

        try:
            await langgraph_manager.close_workspace(workspace_id)
            await WorkspaceStorageService.hard_delete_workspace(username, workspace_id)

            async with SessionLocal() as session:
                workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user_id)
                if workspace is not None:
                    await WorkspaceRepository.delete(session, workspace)

                remaining = await WorkspaceRepository.list_for_user(session, user_id)
                if remaining and not any(ws.is_active == 1 for ws in remaining):
                    remaining[0].is_active = 1

                job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "completed"
                    job.error_message = None

                await session.commit()
        except Exception as exc:  # noqa: BLE001
            async with SessionLocal() as session:
                job = await WorkspaceDeletionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                await session.commit()
