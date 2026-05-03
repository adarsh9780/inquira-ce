"""Asynchronous batch dataset ingestion service."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AppDataSessionLocal
from ..repositories.dataset_ingestion_repository import DatasetIngestionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .dataset_service import DatasetService


class DatasetIngestionService:
    """Manage batch ingestion jobs while serializing workspace DB writes."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()
        self._ingest_lock = asyncio.Lock()

    async def enqueue_dataset_ingestion(
        self,
        session: AsyncSession,
        user,
        workspace_id: str,
        source_paths: list[str],
    ):
        """Create a queued ingestion job and schedule background processing."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        normalized_paths = []
        seen = set()
        for raw_path in source_paths or []:
            path = str(raw_path or "").strip()
            if not path or path in seen:
                continue
            normalized_paths.append(path)
            seen.add(path)
        if not normalized_paths:
            raise HTTPException(status_code=400, detail="At least one dataset path is required")

        job = await DatasetIngestionRepository.create_job(
            session=session,
            principal_id=user.id,
            workspace_id=workspace_id,
            source_paths=normalized_paths,
        )
        await session.commit()
        await session.refresh(job)
        await self._schedule_job(
            job_id=job.id,
            workspace_id=workspace_id,
            principal_id=user.id,
            username=str(getattr(user, "username", "")),
        )
        return job

    async def get_job_for_principal(
        self,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        job_id: str,
    ):
        """Get one ingestion job and enforce ownership/workspace scope."""
        job = await DatasetIngestionRepository.get_by_id(session, job_id)
        if (
            job is None
            or job.owner_principal_id != principal_id
            or str(job.workspace_id) != str(workspace_id)
        ):
            raise HTTPException(status_code=404, detail="Dataset ingestion job not found")
        return job

    async def list_active_jobs_for_workspace(
        self,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ):
        """List active ingestion jobs for one workspace."""
        return await DatasetIngestionRepository.list_active_for_workspace(
            session=session,
            principal_id=principal_id,
            workspace_id=workspace_id,
        )

    async def shutdown(self) -> None:
        """Cancel all active background ingestion tasks."""
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
        username: str,
    ) -> None:
        """Schedule one background ingestion task."""
        async with self._lock:
            if job_id in self._tasks and not self._tasks[job_id].done():
                return
            task = asyncio.create_task(
                self._run_ingestion_job(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    principal_id=principal_id,
                    username=username,
                )
            )
            self._tasks[job_id] = task
            task.add_done_callback(lambda _task: self._tasks.pop(job_id, None))

    async def _run_ingestion_job(
        self,
        *,
        job_id: str,
        workspace_id: str,
        principal_id: str,
        username: str,
    ) -> None:
        """Process one job serially so one workspace kernel writes at a time."""
        async with AppDataSessionLocal() as session:
            job = await DatasetIngestionRepository.get_by_id(session, job_id)
            if job is None:
                return
            job.status = "running"
            job.error_message = None
            await session.commit()

        user = SimpleNamespace(id=principal_id, username=username)
        items = []
        try:
            async with AppDataSessionLocal() as session:
                job = await DatasetIngestionRepository.get_by_id(session, job_id)
                if job is None:
                    return
                items = _read_items(job.items_json)

            for index, item in enumerate(items):
                item["status"] = "running"
                await self._write_items(job_id, items)
                try:
                    async with self._ingest_lock:
                        async with AppDataSessionLocal() as session:
                            dataset = await DatasetService.add_dataset(
                                session=session,
                                user=user,
                                workspace_id=workspace_id,
                                source_path=str(item.get("source_path") or ""),
                            )
                    item["status"] = "completed"
                    item["table_name"] = str(dataset.table_name or "")
                    item["row_count"] = int(dataset.row_count or 0)
                    item["error_message"] = None
                except Exception as exc:  # noqa: BLE001
                    item["status"] = "failed"
                    item["error_message"] = str(getattr(exc, "detail", None) or exc)[:1000]
                finally:
                    items[index] = item
                    await self._write_items(job_id, items)

            completed = sum(1 for item in items if item.get("status") == "completed")
            failed = sum(1 for item in items if item.get("status") == "failed")
            async with AppDataSessionLocal() as session:
                job = await DatasetIngestionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.completed_count = completed
                    job.failed_count = failed
                    job.status = "completed" if failed == 0 else "completed_with_errors"
                    job.error_message = None if failed == 0 else f"{failed} dataset(s) failed to ingest."
                    job.items_json = json.dumps(items)
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            async with AppDataSessionLocal() as session:
                job = await DatasetIngestionRepository.get_by_id(session, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(exc)[:1000]
                await session.commit()

    async def _write_items(self, job_id: str, items: list[dict[str, Any]]) -> None:
        completed = sum(1 for item in items if item.get("status") == "completed")
        failed = sum(1 for item in items if item.get("status") == "failed")
        async with AppDataSessionLocal() as session:
            job = await DatasetIngestionRepository.get_by_id(session, job_id)
            if job is not None:
                job.items_json = json.dumps(items)
                job.completed_count = completed
                job.failed_count = failed
            await session.commit()


def _read_items(items_json: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(items_json or "[]")
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []
