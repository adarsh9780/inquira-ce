from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase
from app.v1.models import Principal, Workspace, WorkspaceDataset
from app.v1.services.dataset_schema_generation_service import DatasetSchemaGenerationService


@pytest.fixture
async def schema_session_factory(tmp_path):
    db_path = tmp_path / "dataset_schema_generation.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


async def _seed_dataset(
    session_factory,
    *,
    workspace_id: str,
    table_name: str,
    schema_status: str = "queued",
) -> None:
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
            WorkspaceDataset(
                workspace_id=workspace_id,
                source_path=f"/tmp/{table_name}.csv",
                source_fingerprint=f"fp-{workspace_id}-{table_name}",
                table_name=table_name,
                schema_path=None,
                schema_status=schema_status,
                schema_error_message=None,
                schema_updated_at=None,
                row_count=1,
                file_type="csv",
            )
        )
        await session.commit()


async def _fetch_dataset(session_factory, workspace_id: str, table_name: str) -> WorkspaceDataset:
    async with session_factory() as session:
        result = await session.execute(
            select(WorkspaceDataset).where(
                WorkspaceDataset.workspace_id == workspace_id,
                WorkspaceDataset.table_name == table_name,
            )
        )
        dataset = result.scalar_one()
        await session.refresh(dataset)
        return dataset


@pytest.mark.asyncio
async def test_schema_generation_service_caps_concurrency_at_four(schema_session_factory, monkeypatch):
    for index in range(5):
        await _seed_dataset(
            schema_session_factory,
            workspace_id="ws-1",
            table_name=f"table_{index}",
        )

    monkeypatch.setattr("app.v1.services.dataset_schema_generation_service.AppDataSessionLocal", schema_session_factory)

    release = asyncio.Event()
    active = {"count": 0, "max": 0}
    started: list[str] = []

    async def fake_runner(*, principal_id: str, workspace_id: str, table_name: str) -> None:
        _ = (principal_id, workspace_id)
        active["count"] += 1
        active["max"] = max(active["max"], active["count"])
        started.append(table_name)
        await release.wait()
        active["count"] -= 1

    service = DatasetSchemaGenerationService(concurrency=4, schema_runner=fake_runner)
    for index in range(5):
        await service.enqueue_dataset_schema_generation(
            principal_id="principal-1",
            workspace_id="ws-1",
            table_name=f"table_{index}",
        )

    for _ in range(30):
        if len(started) == 4:
            break
        await asyncio.sleep(0.02)

    assert active["max"] == 4
    assert len(started) == 4

    release.set()
    for _ in range(30):
        if len(started) == 5:
            break
        await asyncio.sleep(0.02)

    assert len(started) == 5

    await service.shutdown()


@pytest.mark.asyncio
async def test_schema_generation_service_resumes_queued_and_inflight_datasets(schema_session_factory, monkeypatch):
    await _seed_dataset(schema_session_factory, workspace_id="ws-1", table_name="queued_table", schema_status="queued")
    await _seed_dataset(schema_session_factory, workspace_id="ws-1", table_name="inflight_table", schema_status="generating")

    monkeypatch.setattr("app.v1.services.dataset_schema_generation_service.AppDataSessionLocal", schema_session_factory)
    resumed: list[str] = []

    async def fake_runner(*, principal_id: str, workspace_id: str, table_name: str) -> None:
        _ = (principal_id, workspace_id)
        resumed.append(table_name)

    service = DatasetSchemaGenerationService(concurrency=4, schema_runner=fake_runner)
    await service.resume_pending_jobs()

    for _ in range(30):
        if len(resumed) == 2:
            break
        await asyncio.sleep(0.02)

    assert sorted(resumed) == ["inflight_table", "queued_table"]
    assert (await _fetch_dataset(schema_session_factory, "ws-1", "queued_table")).schema_status == "ready"
    assert (await _fetch_dataset(schema_session_factory, "ws-1", "inflight_table")).schema_status == "ready"

    await service.shutdown()


@pytest.mark.asyncio
async def test_schema_generation_service_persists_generating_and_failed_states(schema_session_factory, monkeypatch):
    await _seed_dataset(schema_session_factory, workspace_id="ws-1", table_name="table_fail", schema_status="queued")

    monkeypatch.setattr("app.v1.services.dataset_schema_generation_service.AppDataSessionLocal", schema_session_factory)

    release = asyncio.Event()

    async def fake_runner(*, principal_id: str, workspace_id: str, table_name: str) -> None:
        _ = (principal_id, workspace_id, table_name)
        await release.wait()
        raise RuntimeError("Model timeout")

    service = DatasetSchemaGenerationService(concurrency=4, schema_runner=fake_runner)
    await service.enqueue_dataset_schema_generation(
        principal_id="principal-1",
        workspace_id="ws-1",
        table_name="table_fail",
    )

    for _ in range(30):
        dataset = await _fetch_dataset(schema_session_factory, "ws-1", "table_fail")
        if dataset.schema_status == "generating":
            break
        await asyncio.sleep(0.02)

    dataset = await _fetch_dataset(schema_session_factory, "ws-1", "table_fail")
    assert dataset.schema_status == "generating"

    release.set()
    for _ in range(30):
        dataset = await _fetch_dataset(schema_session_factory, "ws-1", "table_fail")
        if dataset.schema_status == "failed":
            break
        await asyncio.sleep(0.02)

    assert dataset.schema_status == "failed"
    assert dataset.schema_error_message == "Model timeout"
    assert isinstance(dataset.schema_updated_at, datetime)

    await service.shutdown()


def test_backend_startup_wires_dataset_schema_generation_service() -> None:
    source = (Path(__file__).resolve().parents[1] / "app/main.py").read_text(encoding="utf-8")

    assert "from .v1.services.dataset_schema_generation_service import DatasetSchemaGenerationService" in source
    assert "app.state.dataset_schema_generation_service = DatasetSchemaGenerationService()" in source
    assert "DatasetIngestionService(schema_generation_service=app.state.dataset_schema_generation_service)" in source
    assert "await app.state.dataset_schema_generation_service.resume_pending_jobs()" in source
