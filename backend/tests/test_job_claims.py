from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase
from app.v1.models import Principal, Workspace, WorkspaceDatasetDeletionJob, WorkspaceDatasetIngestionJob, WorkspaceDeletionJob
from app.v1.repositories.dataset_deletion_repository import DatasetDeletionRepository
from app.v1.repositories.dataset_ingestion_repository import DatasetIngestionRepository
from app.v1.repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from app.v1.services.dataset_ingestion_service import DatasetIngestionService


def test_job_claim_migration_adds_claim_columns_to_background_jobs(tmp_path) -> None:
    db_path = tmp_path / "job_claims_migration.db"
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = "appdata"

    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        for table_name in (
            "v1_workspace_deletion_jobs",
            "v1_dataset_deletion_jobs",
            "v1_dataset_ingestion_jobs",
        ):
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            assert {
                "claimed_by",
                "lease_expires_at",
                "attempt_count",
                "last_heartbeat_at",
            }.issubset(columns)
    finally:
        engine.dispose()


@pytest.fixture
async def job_session_factory(tmp_path):
    db_path = tmp_path / "job_claims.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_job_repositories_claim_and_reclaim_expired_leases(job_session_factory) -> None:
    async with job_session_factory() as session:
        session.add(Principal(id="principal-1", username_cached="alice", plan_cached="FREE"))
        session.add(
            Workspace(
                id="ws-1",
                owner_principal_id="principal-1",
                name="Data Lab",
                name_normalized="data lab",
                duckdb_path="/tmp/ws-1/workspace.db",
                is_active=1,
            )
        )
        ingestion = WorkspaceDatasetIngestionJob(
            id="ingest-1",
            owner_principal_id="principal-1",
            workspace_id="ws-1",
            status="queued",
            total_count=1,
            completed_count=0,
            failed_count=0,
            items_json=json.dumps([{"source_path": "/tmp/a.csv", "status": "queued"}]),
        )
        dataset_delete = WorkspaceDatasetDeletionJob(
            id="delete-1",
            owner_principal_id="principal-1",
            workspace_id="ws-1",
            table_name="batting",
            status="queued",
        )
        workspace_delete = WorkspaceDeletionJob(
            id="ws-delete-1",
            owner_principal_id="principal-1",
            workspace_id="ws-1",
            status="queued",
        )
        session.add_all([ingestion, dataset_delete, workspace_delete])
        await session.commit()

    async with job_session_factory() as session:
        claimed = await DatasetIngestionRepository.claim_job(
            session,
            job_id="ingest-1",
            worker_id="worker-a",
            lease_seconds=30,
        )
        assert claimed is not None
        duplicate = await DatasetIngestionRepository.claim_job(
            session,
            job_id="ingest-1",
            worker_id="worker-b",
            lease_seconds=30,
        )
        assert duplicate is None

        await WorkspaceDeletionRepository.claim_job(
            session,
            job_id="ws-delete-1",
            worker_id="worker-a",
            lease_seconds=30,
        )
        await DatasetDeletionRepository.claim_job(
            session,
            job_id="delete-1",
            worker_id="worker-a",
            lease_seconds=30,
        )

    async with job_session_factory() as session:
        ingestion = await DatasetIngestionRepository.get_by_id(session, "ingest-1")
        dataset_delete = await DatasetDeletionRepository.get_by_id(session, "delete-1")
        workspace_delete = await WorkspaceDeletionRepository.get_by_id(session, "ws-delete-1")
        ingestion.lease_expires_at = ingestion.lease_expires_at.replace(year=2020)  # type: ignore[union-attr]
        dataset_delete.lease_expires_at = dataset_delete.lease_expires_at.replace(year=2020)  # type: ignore[union-attr]
        workspace_delete.lease_expires_at = workspace_delete.lease_expires_at.replace(year=2020)  # type: ignore[union-attr]
        await session.commit()

    async with job_session_factory() as session:
        reclaimed_ingest = await DatasetIngestionRepository.claim_job(
            session,
            job_id="ingest-1",
            worker_id="worker-b",
            lease_seconds=30,
        )
        reclaimed_dataset_delete = await DatasetDeletionRepository.claim_job(
            session,
            job_id="delete-1",
            worker_id="worker-b",
            lease_seconds=30,
        )
        reclaimed_workspace_delete = await WorkspaceDeletionRepository.claim_job(
            session,
            job_id="ws-delete-1",
            worker_id="worker-b",
            lease_seconds=30,
        )

    assert reclaimed_ingest is not None
    assert reclaimed_dataset_delete is not None
    assert reclaimed_workspace_delete is not None
    assert reclaimed_ingest.claimed_by == "worker-b"
    assert reclaimed_dataset_delete.claimed_by == "worker-b"
    assert reclaimed_workspace_delete.claimed_by == "worker-b"


@pytest.mark.asyncio
async def test_dataset_ingestion_service_resumes_pending_jobs(job_session_factory, monkeypatch) -> None:
    async with job_session_factory() as session:
        principal = Principal(id="principal-1", username_cached="alice", plan_cached="FREE")
        workspace = Workspace(
            id="ws-1",
            owner_principal_id="principal-1",
            name="Data Lab",
            name_normalized="data lab",
            duckdb_path="/tmp/ws-1/workspace.db",
            is_active=1,
        )
        session.add_all([principal, workspace])
        session.add(
            WorkspaceDatasetIngestionJob(
                id="ingest-1",
                owner_principal_id="principal-1",
                workspace_id="ws-1",
                status="running",
                total_count=1,
                completed_count=0,
                failed_count=0,
                items_json=json.dumps([{"source_path": "/tmp/a.csv", "status": "queued"}]),
                claimed_by="stale-worker",
            )
        )
        await session.commit()

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", job_session_factory)
    scheduled: list[tuple[str, str, str, str]] = []

    service = DatasetIngestionService()

    async def fake_schedule_job(*, job_id: str, workspace_id: str, principal_id: str, username: str) -> None:
        scheduled.append((job_id, workspace_id, principal_id, username))

    monkeypatch.setattr(service, "_schedule_job", fake_schedule_job)

    await service.resume_pending_jobs()

    assert scheduled == [("ingest-1", "ws-1", "principal-1", "alice")]


@pytest.mark.asyncio
async def test_dataset_ingestion_service_serializes_same_workspace_but_allows_other_workspaces(
    job_session_factory,
    monkeypatch,
) -> None:
    async with job_session_factory() as session:
        principal = Principal(id="principal-1", username_cached="alice", plan_cached="FREE")
        session.add(principal)
        session.add_all(
            [
                Workspace(
                    id="ws-1",
                    owner_principal_id="principal-1",
                    name="Alpha",
                    name_normalized="alpha",
                    duckdb_path="/tmp/ws-1/workspace.db",
                    is_active=1,
                ),
                Workspace(
                    id="ws-2",
                    owner_principal_id="principal-1",
                    name="Beta",
                    name_normalized="beta",
                    duckdb_path="/tmp/ws-2/workspace.db",
                    is_active=0,
                ),
            ]
        )
        session.add_all(
            [
                WorkspaceDatasetIngestionJob(
                    id="ingest-a",
                    owner_principal_id="principal-1",
                    workspace_id="ws-1",
                    status="queued",
                    total_count=1,
                    completed_count=0,
                    failed_count=0,
                    items_json=json.dumps([{"source_path": "/tmp/a.csv", "status": "queued"}]),
                ),
                WorkspaceDatasetIngestionJob(
                    id="ingest-b",
                    owner_principal_id="principal-1",
                    workspace_id="ws-1",
                    status="queued",
                    total_count=1,
                    completed_count=0,
                    failed_count=0,
                    items_json=json.dumps([{"source_path": "/tmp/b.csv", "status": "queued"}]),
                ),
                WorkspaceDatasetIngestionJob(
                    id="ingest-c",
                    owner_principal_id="principal-1",
                    workspace_id="ws-2",
                    status="queued",
                    total_count=1,
                    completed_count=0,
                    failed_count=0,
                    items_json=json.dumps([{"source_path": "/tmp/c.csv", "status": "queued"}]),
                ),
            ]
        )
        await session.commit()

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.AppDataSessionLocal", job_session_factory)
    active_per_workspace: dict[str, int] = {}
    max_per_workspace: dict[str, int] = {}
    overall_active = {"count": 0, "max": 0}

    async def fake_add_dataset(*, session, user, workspace_id: str, source_path: str):
        _ = (session, user, source_path)
        active_per_workspace[workspace_id] = active_per_workspace.get(workspace_id, 0) + 1
        overall_active["count"] += 1
        max_per_workspace[workspace_id] = max(
            max_per_workspace.get(workspace_id, 0),
            active_per_workspace[workspace_id],
        )
        overall_active["max"] = max(overall_active["max"], overall_active["count"])
        await asyncio.sleep(0.05)
        active_per_workspace[workspace_id] -= 1
        overall_active["count"] -= 1
        return SimpleNamespace(table_name=f"table_{workspace_id}", row_count=1)

    monkeypatch.setattr("app.v1.services.dataset_ingestion_service.DatasetService.add_dataset", fake_add_dataset)
    monkeypatch.setattr(
        "app.v1.services.dataset_ingestion_service.DatasetIngestionService._ensure_workspace_runtime_ready",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )

    service = DatasetIngestionService()
    await asyncio.gather(
        service._run_ingestion_job(job_id="ingest-a", workspace_id="ws-1", principal_id="principal-1", username="alice"),
        service._run_ingestion_job(job_id="ingest-b", workspace_id="ws-1", principal_id="principal-1", username="alice"),
        service._run_ingestion_job(job_id="ingest-c", workspace_id="ws-2", principal_id="principal-1", username="alice"),
    )

    assert max_per_workspace["ws-1"] == 1
    assert overall_active["max"] >= 2
