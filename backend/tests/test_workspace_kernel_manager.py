import asyncio
from types import SimpleNamespace

import pytest

from app.services.workspace_kernel_manager import (
    WorkspaceKernelManager,
    WorkspaceKernelSession,
)


def _session(workspace_id: str, workspace_duckdb_path: str) -> WorkspaceKernelSession:
    return WorkspaceKernelSession(
        workspace_id=workspace_id,
        workspace_duckdb_path=workspace_duckdb_path,
        manager=SimpleNamespace(),
        client=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_get_or_start_session_reuses_workspace_kernel():
    manager = WorkspaceKernelManager(idle_minutes=30)
    calls = {"count": 0}

    async def fake_start(*, workspace_id: str, workspace_duckdb_path: str, config):
        _ = config
        calls["count"] += 1
        return _session(workspace_id, workspace_duckdb_path)

    manager._start_session = fake_start  # type: ignore[method-assign]

    cfg = SimpleNamespace()
    session_a = await manager._get_or_start_session(  # type: ignore[attr-defined]
        workspace_id="ws-1",
        workspace_duckdb_path="/tmp/a.duckdb",
        config=cfg,
    )
    session_b = await manager._get_or_start_session(  # type: ignore[attr-defined]
        workspace_id="ws-1",
        workspace_duckdb_path="/tmp/a.duckdb",
        config=cfg,
    )

    assert calls["count"] == 1
    assert session_a is session_b


@pytest.mark.asyncio
async def test_reset_workspace_removes_cached_session():
    manager = WorkspaceKernelManager(idle_minutes=30)
    manager._sessions["ws-1"] = _session("ws-1", "/tmp/a.duckdb")
    shutdown_calls = {"count": 0}

    async def fake_shutdown(session):
        _ = session
        shutdown_calls["count"] += 1

    manager._shutdown_session = fake_shutdown  # type: ignore[method-assign]

    assert await manager.reset_workspace("ws-1") is True
    assert await manager.reset_workspace("ws-1") is False
    assert shutdown_calls["count"] == 1


@pytest.mark.asyncio
async def test_execute_serializes_requests_per_workspace():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    manager._sessions["ws-1"] = session
    order: list[str] = []

    async def fake_get_or_start_session(*, workspace_id, workspace_duckdb_path, config):
        _ = (workspace_id, workspace_duckdb_path, config)
        return session

    async def fake_execute_on_session(current_session, code):
        _ = current_session
        order.append(f"start-{code}")
        await asyncio.sleep(0.01)
        order.append(f"end-{code}")
        return {
            "success": True,
            "stdout": code,
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
        }

    manager._get_or_start_session = fake_get_or_start_session  # type: ignore[method-assign]
    manager._execute_on_session = fake_execute_on_session  # type: ignore[method-assign]

    cfg = SimpleNamespace(runner_policy=SimpleNamespace(timeout_seconds=60))
    await asyncio.gather(
        manager.execute(
            workspace_id="ws-1",
            workspace_duckdb_path="/tmp/a.duckdb",
            code="a",
            timeout=2,
            config=cfg,
        ),
        manager.execute(
            workspace_id="ws-1",
            workspace_duckdb_path="/tmp/a.duckdb",
            code="b",
            timeout=2,
            config=cfg,
        ),
    )

    assert order in (
        ["start-a", "end-a", "start-b", "end-b"],
        ["start-b", "end-b", "start-a", "end-a"],
    )
