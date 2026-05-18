from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1 import models  # noqa: F401
from app.v1.api import runtime as runtime_api
from app.v1.db.base import AppDataBase
from app.v1.models import Principal, Workspace, WorkspaceDatasetDeletionJob, WorkspaceDeletionJob
from app.v1.repositories.dataset_deletion_repository import DatasetDeletionRepository
from app.v1.repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from app.v1.services.dataset_deletion_service import DatasetDeletionService
from app.v1.services.workspace_deletion_service import WorkspaceDeletionService


@pytest.fixture
async def maintenance_session_factory(tmp_path):
    db_path = tmp_path / "workspace_maintenance_conflicts.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_hard_reset_returns_structured_busy_conflict(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-hard-reset"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.db"
    duckdb_path.write_text("db", encoding="utf-8")
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = session, user_id
        assert workspace_id == "ws-hard-reset"
        return workspace

    async def fake_drain_runtime(*, workspace_id, user_id):
        assert workspace_id == "ws-hard-reset"
        assert user_id == "user-1"

    async def fake_acquire(*args, **kwargs):
        _ = args
        raise HTTPException(
            status_code=409,
            detail={
                "code": "workspace_busy",
                "detail": "Workspace ws-hard-reset is busy because workspace_runtime is still active.",
                "resource": "ws-hard-reset",
                "current_operation": "workspace_runtime",
            },
        )

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "delete_workspace_runner_environment", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        runtime_api.WorkspaceMaintenanceService,
        "drain_runtime",
        fake_drain_runtime,
    )
    monkeypatch.setattr(
        runtime_api.WorkspaceMaintenanceService,
        "acquire_lease_or_raise",
        fake_acquire,
    )

    with pytest.raises(HTTPException) as exc:
        await runtime_api.hard_reset_workspace_runtime_endpoint(
            workspace_id="ws-hard-reset",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "workspace_busy"
    assert exc.value.detail["current_operation"] == "workspace_runtime"


@pytest.mark.asyncio
async def test_dataset_deletion_service_marks_job_failed_when_workspace_busy(
    maintenance_session_factory,
    monkeypatch,
) -> None:
    async with maintenance_session_factory() as session:
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
        session.add(
            WorkspaceDatasetDeletionJob(
                id="delete-1",
                owner_principal_id="principal-1",
                workspace_id="ws-1",
                table_name="orders",
                status="queued",
            )
        )
        await session.commit()

    monkeypatch.setattr("app.v1.services.dataset_deletion_service.AppDataSessionLocal", maintenance_session_factory)

    async def fake_drain_runtime(*, workspace_id, user_id):
        assert workspace_id == "ws-1"
        assert user_id == "principal-1"

    async def fake_acquire(*args, **kwargs):
        _ = args, kwargs
        raise HTTPException(
            status_code=409,
            detail={
                "code": "workspace_busy",
                "detail": "Workspace ws-1 is busy because workspace_runtime is still active.",
                "resource": "ws-1",
                "current_operation": "workspace_runtime",
            },
        )

    monkeypatch.setattr(
        "app.v1.services.dataset_deletion_service.WorkspaceMaintenanceService.drain_runtime",
        fake_drain_runtime,
    )
    monkeypatch.setattr(
        "app.v1.services.dataset_deletion_service.WorkspaceMaintenanceService.acquire_lease_or_raise",
        fake_acquire,
    )

    service = DatasetDeletionService()
    await service._run_delete_job(
        job_id="delete-1",
        workspace_id="ws-1",
        principal_id="principal-1",
        table_name="orders",
    )

    async with maintenance_session_factory() as session:
        job = await DatasetDeletionRepository.get_by_id(session, "delete-1")

    assert job is not None
    assert job.status == "failed"
    assert '"code": "workspace_busy"' in str(job.error_message)


@pytest.mark.asyncio
async def test_workspace_deletion_service_marks_job_failed_when_workspace_busy(
    maintenance_session_factory,
    monkeypatch,
) -> None:
    async with maintenance_session_factory() as session:
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
        session.add(
            WorkspaceDeletionJob(
                id="delete-1",
                owner_principal_id="principal-1",
                workspace_id="ws-1",
                status="queued",
            )
        )
        await session.commit()

    monkeypatch.setattr("app.v1.services.workspace_deletion_service.AppDataSessionLocal", maintenance_session_factory)

    async def fake_drain_runtime(*, workspace_id, user_id):
        assert workspace_id == "ws-1"
        assert user_id == "principal-1"

    async def fake_acquire(*args, **kwargs):
        _ = args, kwargs
        raise HTTPException(
            status_code=409,
            detail={
                "code": "workspace_busy",
                "detail": "Workspace ws-1 is busy because workspace_runtime is still active.",
                "resource": "ws-1",
                "current_operation": "workspace_runtime",
            },
        )

    monkeypatch.setattr(
        "app.v1.services.workspace_deletion_service.WorkspaceMaintenanceService.drain_runtime",
        fake_drain_runtime,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_deletion_service.WorkspaceMaintenanceService.acquire_lease_or_raise",
        fake_acquire,
    )

    class _FakeLanggraphManager:
        async def close_workspace(self, workspace_id: str) -> None:
            assert workspace_id == "ws-1"

    service = WorkspaceDeletionService()
    await service._run_delete_job(
        job_id="delete-1",
        workspace_id="ws-1",
        principal_id="principal-1",
        username="alice",
        langgraph_manager=_FakeLanggraphManager(),
    )

    async with maintenance_session_factory() as session:
        job = await WorkspaceDeletionRepository.get_by_id(session, "delete-1")

    assert job is not None
    assert job.status == "failed"
    assert '"code": "workspace_busy"' in str(job.error_message)
