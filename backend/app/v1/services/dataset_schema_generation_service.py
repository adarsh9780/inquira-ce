"""Background schema generation queue for workspace datasets."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AppDataSessionLocal
from ..models import Workspace, WorkspaceDataset
from .dataset_service import DatasetService


class DatasetSchemaGenerationService:
    """Queue and run dataset schema generation with bounded concurrency."""

    def __init__(self, *, concurrency: int = 4, schema_runner=None) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, int(concurrency)))
        self._schema_runner = schema_runner or self._default_schema_runner

    async def enqueue_dataset_schema_generation(
        self,
        *,
        principal_id: str,
        workspace_id: str,
        table_name: str,
    ) -> None:
        normalized_workspace_id = str(workspace_id or "").strip()
        normalized_table_name = str(table_name or "").strip()
        if not normalized_workspace_id or not normalized_table_name:
            return
        async with AppDataSessionLocal() as session:
            dataset = await self._get_dataset(session, normalized_workspace_id, normalized_table_name)
            if dataset is None:
                return
            dataset.schema_status = DatasetService.SCHEMA_STATUS_QUEUED
            dataset.schema_error_message = None
            await session.commit()
        await self._schedule(
            principal_id=str(principal_id or "").strip(),
            workspace_id=normalized_workspace_id,
            table_name=normalized_table_name,
        )

    async def resume_pending_jobs(self) -> None:
        async with AppDataSessionLocal() as session:
            result = await session.execute(
                select(WorkspaceDataset, Workspace.owner_principal_id)
                .join(Workspace, Workspace.id == WorkspaceDataset.workspace_id)
                .where(
                    WorkspaceDataset.schema_status.in_(
                        [
                            DatasetService.SCHEMA_STATUS_QUEUED,
                            DatasetService.SCHEMA_STATUS_GENERATING,
                        ]
                    )
                )
                .order_by(WorkspaceDataset.updated_at.asc(), WorkspaceDataset.id.asc())
            )
            rows = list(result.all())
            for dataset, _principal_id in rows:
                if dataset.schema_status == DatasetService.SCHEMA_STATUS_GENERATING:
                    dataset.schema_status = DatasetService.SCHEMA_STATUS_QUEUED
            await session.commit()

        for dataset, principal_id in rows:
            await self._schedule(
                principal_id=str(principal_id or "").strip(),
                workspace_id=str(dataset.workspace_id or "").strip(),
                table_name=str(dataset.table_name or "").strip(),
            )

    async def shutdown(self) -> None:
        async with self._lock:
            tasks = list(self._tasks.values())
            self._tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _schedule(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
        key = self._job_key(workspace_id, table_name)
        async with self._lock:
            existing = self._tasks.get(key)
            if existing is not None and not existing.done():
                return
            task = asyncio.create_task(
                self._run_job(
                    principal_id=principal_id,
                    workspace_id=workspace_id,
                    table_name=table_name,
                )
            )
            self._tasks[key] = task
            task.add_done_callback(self._build_task_cleanup_callback(key))

    async def _run_job(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
        async with self._semaphore:
            async with AppDataSessionLocal() as session:
                dataset = await self._get_dataset(session, workspace_id, table_name)
                if dataset is None:
                    return
                dataset.schema_status = DatasetService.SCHEMA_STATUS_GENERATING
                dataset.schema_error_message = None
                await session.commit()

            try:
                await self._schema_runner(
                    principal_id=principal_id,
                    workspace_id=workspace_id,
                    table_name=table_name,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                await self._mark_dataset_result(
                    workspace_id=workspace_id,
                    table_name=table_name,
                    status=DatasetService.SCHEMA_STATUS_FAILED,
                    error_message=str(exc).strip() or "Schema generation failed.",
                )
                return

            await self._mark_dataset_result(
                workspace_id=workspace_id,
                table_name=table_name,
                status=DatasetService.SCHEMA_STATUS_READY,
                error_message=None,
            )

    async def _mark_dataset_result(
        self,
        *,
        workspace_id: str,
        table_name: str,
        status: str,
        error_message: str | None,
    ) -> None:
        async with AppDataSessionLocal() as session:
            dataset = await self._get_dataset(session, workspace_id, table_name)
            if dataset is None:
                return
            dataset.schema_status = status
            dataset.schema_error_message = error_message
            dataset.schema_updated_at = datetime.now().astimezone()
            await session.commit()

    async def _default_schema_runner(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
        from ..api import runtime as runtime_api

        async with AppDataSessionLocal() as session:
            await runtime_api.regenerate_workspace_dataset_schema(
                workspace_id=workspace_id,
                table_name=table_name,
                payload=runtime_api.RegenerateSchemaRequest(),
                session=session,
                current_user=SimpleNamespace(id=principal_id, username=f"schema-worker-{uuid.uuid4()}"),
            )

    @staticmethod
    async def _get_dataset(session: AsyncSession, workspace_id: str, table_name: str) -> WorkspaceDataset | None:
        result = await session.execute(
            select(WorkspaceDataset).where(
                WorkspaceDataset.workspace_id == workspace_id,
                WorkspaceDataset.table_name == table_name,
            )
        )
        return cast(WorkspaceDataset | None, result.scalar_one_or_none())

    @staticmethod
    def _job_key(workspace_id: str, table_name: str) -> str:
        return f"{workspace_id}:{table_name}"

    def _build_task_cleanup_callback(self, key: str):
        def _cleanup(_task: asyncio.Task[Any]) -> None:
            self._tasks.pop(key, None)

        return _cleanup
