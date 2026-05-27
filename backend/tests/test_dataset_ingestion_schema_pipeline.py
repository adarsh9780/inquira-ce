from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase
from app.v1.models import Principal, Workspace, WorkspaceDatasetIngestionJob
from app.v1.repositories.dataset_ingestion_repository import DatasetIngestionRepository
from app.v1.services.dataset_ingestion_service import DatasetIngestionService


@pytest.fixture
async def ingestion_session_factory(tmp_path):
    db_path = tmp_path / "dataset_ingestion_schema_pipeline.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


async def _seed_ingestion_job(session_factory, *, job_id: str, workspace_id: str, source_paths: list[str]) -> None:
    async with session_factory() as session:
        principal = await session.get(Principal, "principal-1")
        if principal is None:
            session.add(Principal(id="principal-1", username_cached="alice", plan_cached="FREE"))
        workspace = await session.get(Workspace, workspace_id)
        if workspace is None:
            session.add(
                Workspace(
                    id=workspace_id,
                    owner_principal_id="principal-1",
                    name=workspace_id.upper(),
                    name_normalized=workspace_id.lower(),
                    duckdb_path=f"/tmp/{workspace_id}/workspace.db",
                    is_active=1,
                )
            )
        session.add(
            WorkspaceDatasetIngestionJob(
                id=job_id,
                owner_principal_id="principal-1",
                workspace_id=workspace_id,
                status="queued",
                total_count=len(source_paths),
                completed_count=0,
                failed_count=0,
                items_json=json.dumps([{"source_path": path, "status": "queued"} for path in source_paths]),
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_ingestion_enqueues_schema_as_soon_as_each_import_completes(
    ingestion_session_factory,
    monkeypatch,
):
    await _seed_ingestion_job(
        ingestion_session_factory,
        job_id="ingest-1",
        workspace_id="ws-1",
        source_paths=["/tmp/a.csv", "/tmp/b.csv"],
    )

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", ingestion_session_factory)

    first_schema_started = asyncio.Event()
    overlap_observed = {"value": False}
    imports_started: list[str] = []
    imports_completed: list[str] = []
    enqueued_tables: list[str] = []

    class FakeSchemaGenerationService:
        async def enqueue_dataset_schema_generation(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
            _ = principal_id
            enqueued_tables.append(table_name)
            if table_name == "table_a":
                first_schema_started.set()

                async def _background():
                    await asyncio.sleep(0.1)

                asyncio.create_task(_background())

    async def fake_add_dataset(*, session, user, workspace_id: str, source_path: str):
        _ = (session, user, workspace_id)
        imports_started.append(source_path)
        if source_path.endswith("b.csv"):
            overlap_observed["value"] = first_schema_started.is_set()
        await asyncio.sleep(0.02)
        imports_completed.append(source_path)
        table_name = "table_a" if source_path.endswith("a.csv") else "table_b"
        return SimpleNamespace(table_name=table_name, row_count=1)

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.DatasetService.add_dataset", fake_add_dataset)
    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.bootstrap_workspace_runtime", _ready_runtime)

    service = DatasetIngestionService(schema_generation_service=FakeSchemaGenerationService())
    await service._run_ingestion_job(
        job_id="ingest-1",
        workspace_id="ws-1",
        principal_id="principal-1",
        username="alice",
    )

    assert imports_started == ["/tmp/a.csv", "/tmp/b.csv"]
    assert imports_completed == ["/tmp/a.csv", "/tmp/b.csv"]
    assert enqueued_tables == ["table_a", "table_b"]
    assert overlap_observed["value"] is True


@pytest.mark.asyncio
async def test_ingestion_keeps_importing_when_schema_enqueue_fails(
    ingestion_session_factory,
    monkeypatch,
):
    await _seed_ingestion_job(
        ingestion_session_factory,
        job_id="ingest-2",
        workspace_id="ws-1",
        source_paths=["/tmp/a.csv", "/tmp/b.csv"],
    )

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", ingestion_session_factory)
    imported_sources: list[str] = []

    class FlakySchemaGenerationService:
        async def enqueue_dataset_schema_generation(self, *, principal_id: str, workspace_id: str, table_name: str) -> None:
            _ = (principal_id, workspace_id)
            if table_name == "table_a":
                raise RuntimeError("queue unavailable")

    async def fake_add_dataset(*, session, user, workspace_id: str, source_path: str):
        _ = (session, user, workspace_id)
        imported_sources.append(source_path)
        await asyncio.sleep(0.01)
        table_name = "table_a" if source_path.endswith("a.csv") else "table_b"
        return SimpleNamespace(table_name=table_name, row_count=1)

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.DatasetService.add_dataset", fake_add_dataset)
    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.bootstrap_workspace_runtime", _ready_runtime)

    service = DatasetIngestionService(schema_generation_service=FlakySchemaGenerationService())
    await service._run_ingestion_job(
        job_id="ingest-2",
        workspace_id="ws-1",
        principal_id="principal-1",
        username="alice",
    )

    async with ingestion_session_factory() as session:
        job = await DatasetIngestionRepository.get_by_id(session, "ingest-2")

    assert imported_sources == ["/tmp/a.csv", "/tmp/b.csv"]
    assert job is not None
    assert job.status == "completed"
    assert job.completed_count == 2
    assert job.failed_count == 0


async def _ready_runtime(*, workspace_id: str, workspace_duckdb_path: str, progress_callback=None) -> bool:
    _ = workspace_id, workspace_duckdb_path, progress_callback
    return True


@pytest.mark.asyncio
async def test_ingestion_waits_for_workspace_runtime_before_import(
    ingestion_session_factory,
    monkeypatch,
):
    await _seed_ingestion_job(
        ingestion_session_factory,
        job_id="ingest-3",
        workspace_id="ws-1",
        source_paths=["/tmp/a.csv"],
    )

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", ingestion_session_factory)
    runtime_ready = asyncio.Event()
    imports_started: list[str] = []

    async def fake_bootstrap(*, workspace_id: str, workspace_duckdb_path: str, progress_callback=None):
        _ = workspace_id, workspace_duckdb_path, progress_callback
        await runtime_ready.wait()
        return True

    async def fake_add_dataset(*, session, user, workspace_id: str, source_path: str):
        _ = session, user, workspace_id
        imports_started.append(source_path)
        return SimpleNamespace(table_name="table_a", row_count=1)

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.bootstrap_workspace_runtime", fake_bootstrap)
    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.DatasetService.add_dataset", fake_add_dataset)

    service = DatasetIngestionService()
    task = asyncio.create_task(
        service._run_ingestion_job(
            job_id="ingest-3",
            workspace_id="ws-1",
            principal_id="principal-1",
            username="alice",
        )
    )
    await asyncio.sleep(0.05)
    assert imports_started == []

    runtime_ready.set()
    await task
    assert imports_started == ["/tmp/a.csv"]


@pytest.mark.asyncio
async def test_ingestion_marks_item_failed_when_runtime_bootstrap_fails(
    ingestion_session_factory,
    monkeypatch,
):
    await _seed_ingestion_job(
        ingestion_session_factory,
        job_id="ingest-4",
        workspace_id="ws-1",
        source_paths=["/tmp/a.csv"],
    )

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", ingestion_session_factory)

    async def fake_bootstrap(*, workspace_id: str, workspace_duckdb_path: str, progress_callback=None):
        _ = workspace_id, workspace_duckdb_path, progress_callback
        raise RuntimeError("runtime unavailable")

    async def fake_add_dataset(*, session, user, workspace_id: str, source_path: str):
        _ = session, user, workspace_id, source_path
        raise AssertionError("import should not start when runtime bootstrap fails")

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.bootstrap_workspace_runtime", fake_bootstrap)
    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.DatasetService.add_dataset", fake_add_dataset)

    service = DatasetIngestionService()
    await service._run_ingestion_job(
        job_id="ingest-4",
        workspace_id="ws-1",
        principal_id="principal-1",
        username="alice",
    )

    async with ingestion_session_factory() as session:
        job = await DatasetIngestionRepository.get_by_id(session, "ingest-4")

    items = json.loads(job.items_json)
    assert job.status == "completed_with_errors"
    assert job.completed_count == 0
    assert job.failed_count == 1
    assert items[0]["status"] == "failed"
    assert "runtime unavailable" in items[0]["error_message"]
