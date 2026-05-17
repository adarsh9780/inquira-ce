from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_access.coordinator import LeaseConflictError
from app.data_access.coordinator import ResourceLeaseCoordinator
from app.data_access.workspace_db import WorkspaceOfflineAdapter, WorkspaceRuntimeAdapter
from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase
from app.v1.services.workspace_storage_service import WorkspaceStorageService


@pytest.fixture
async def lease_session(tmp_path):
    db_path = tmp_path / "workspace-db-leases.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_runtime_adapter_delegates_to_kernel(monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def fake_schema(*, workspace_id: str, table_name: str, allow_sample_values: bool = False):
        calls["workspace_id"] = workspace_id
        calls["table_name"] = table_name
        calls["allow_sample_values"] = allow_sample_values
        return [{"name": "runs", "dtype": "BIGINT", "description": "", "samples": [], "aliases": []}]

    monkeypatch.setattr("app.services.code_executor.get_workspace_table_schema_via_kernel", fake_schema)

    rows = await WorkspaceRuntimeAdapter().get_table_columns(
        workspace_id="ws-1",
        table_name="batting",
    )

    assert calls == {
        "workspace_id": "ws-1",
        "table_name": "batting",
        "allow_sample_values": False,
    }
    assert rows == [{"name": "runs", "dtype": "BIGINT", "description": "", "samples": [], "aliases": []}]


@pytest.mark.asyncio
async def test_workspace_offline_adapter_requires_maintenance_lease(lease_session, tmp_path) -> None:
    db_path = tmp_path / "workspace.db"
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE batting(runs INTEGER)")
    con.close()

    adapter = WorkspaceOfflineAdapter(session=lease_session, owner_token="maintenance-owner")
    with pytest.raises(LeaseConflictError, match="Active owned lease"):
        await adapter.drop_table(
            workspace_id="ws-1",
            workspace_duckdb_path=str(db_path),
            table_name="batting",
        )


@pytest.mark.asyncio
async def test_workspace_offline_adapter_drops_table_with_maintenance_lease(lease_session, tmp_path) -> None:
    db_path = tmp_path / "workspace.db"
    con = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE batting(runs INTEGER)")
    con.close()

    coordinator = ResourceLeaseCoordinator()
    await coordinator.acquire_workspace_maintenance_lease(
        lease_session,
        workspace_id="ws-1",
        owner_token="maintenance-owner",
    )
    await lease_session.commit()

    adapter = WorkspaceOfflineAdapter(
        session=lease_session,
        owner_token="maintenance-owner",
        coordinator=coordinator,
    )
    await adapter.drop_table(
        workspace_id="ws-1",
        workspace_duckdb_path=str(db_path),
        table_name="batting",
    )

    verify = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = verify.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'batting'"
        ).fetchone()
    finally:
        verify.close()
    assert rows == (0,)


@pytest.mark.asyncio
async def test_workspace_storage_service_bootstraps_workspace_db(monkeypatch, tmp_path) -> None:
    user_root = tmp_path / "workspaces-root"
    monkeypatch.setattr(
        WorkspaceStorageService,
        "_user_root",
        staticmethod(lambda _username: user_root),
    )

    workspace_dir = await WorkspaceStorageService.ensure_workspace_dirs("alice", "ws-1")

    assert workspace_dir == user_root / "ws-1"
    assert (workspace_dir / "workspace.db").exists() is True


def test_migrated_workspace_services_do_not_open_duckdb_directly() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        repo_root / "app" / "v1" / "services" / "chat_service.py",
        repo_root / "app" / "v1" / "services" / "dataset_deletion_service.py",
        repo_root / "app" / "v1" / "services" / "workspace_storage_service.py",
    ]

    for path in targets:
        source = path.read_text(encoding="utf-8")
        assert "duckdb.connect" not in source, f"unexpected raw duckdb access in {path.name}"
