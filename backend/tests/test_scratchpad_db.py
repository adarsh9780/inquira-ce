from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_access import ScratchpadOfflineAdapter, ScratchpadRuntimeAdapter
from app.data_access.coordinator import LeaseConflictError, ResourceLeaseCoordinator
from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase


@pytest.fixture
async def adapter_session(tmp_path):
    db_path = tmp_path / "scratchpad-adapter.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_scratchpad_runtime_adapter_delegates_to_kernel(monkeypatch) -> None:
    async def fake_usage(workspace_id: str):
        assert workspace_id == "workspace-1"
        return {"duckdb_bytes": 10, "figure_count": 2}

    monkeypatch.setattr(
        "app.data_access.scratchpad_db.get_workspace_artifact_usage_via_kernel",
        fake_usage,
    )

    usage = await ScratchpadRuntimeAdapter().get_workspace_artifact_usage(
        workspace_id="workspace-1"
    )

    assert usage == {"duckdb_bytes": 10, "figure_count": 2}


@pytest.mark.asyncio
async def test_scratchpad_offline_adapter_refuses_access_without_maintenance_lease(
    adapter_session,
    tmp_path,
) -> None:
    workspace_db = tmp_path / "workspace.db"
    workspace_db.touch()
    adapter = ScratchpadOfflineAdapter(
        session=adapter_session,
        owner_token="owner-1",
    )

    with pytest.raises(LeaseConflictError, match="Active owned lease"):
        await adapter.get_workspace_artifact_usage(
            workspace_id="workspace-1",
            workspace_duckdb_path=str(workspace_db),
        )


@pytest.mark.asyncio
async def test_scratchpad_offline_adapter_allows_access_with_maintenance_lease(
    adapter_session,
    tmp_path,
    monkeypatch,
) -> None:
    workspace_db = tmp_path / "workspace.db"
    workspace_db.touch()
    coordinator = ResourceLeaseCoordinator()
    await coordinator.acquire_workspace_maintenance_lease(
        adapter_session,
        workspace_id="workspace-1",
        owner_token="owner-1",
    )
    await adapter_session.commit()

    def fake_usage(self, *, workspace_duckdb_path: str):
        _ = self
        assert workspace_duckdb_path == str(workspace_db)
        return {"duckdb_bytes": 25, "figure_count": 4}

    monkeypatch.setattr(
        "app.data_access.scratchpad_db.ArtifactScratchpadStore.get_workspace_artifact_usage",
        fake_usage,
    )

    adapter = ScratchpadOfflineAdapter(
        session=adapter_session,
        owner_token="owner-1",
        coordinator=coordinator,
    )
    usage = await adapter.get_workspace_artifact_usage(
        workspace_id="workspace-1",
        workspace_duckdb_path=str(workspace_db),
    )

    assert usage == {"duckdb_bytes": 25, "figure_count": 4}
