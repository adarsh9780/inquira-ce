from __future__ import annotations

import asyncio
from pathlib import Path

import duckdb

from inquira_data_worker.runtime import WorkerRuntime


def test_runtime_rpc_manages_workspace_kernel_lifecycle(tmp_path: Path) -> None:
    async def scenario() -> None:
        catalog = tmp_path / "workspace.duckdb"
        connection = duckdb.connect(str(catalog))
        connection.close()
        runtime = WorkerRuntime(idle_seconds=300)
        events: list[dict] = []
        try:
            pong = await runtime.handle({"id": "ping", "method": "ping", "params": {}}, events.append)
            assert pong["result"]["status"] == "ready"
            executed = await runtime.handle({
                "id": "execute",
                "method": "kernel_execute",
                "params": {
                    "workspace_id": "workspace-1",
                    "database_path": str(catalog),
                    "code": "21 * 2",
                    "run_id": "run-1",
                    "artifact_dir": str(tmp_path / "artifacts"),
                    "timeout_seconds": 10,
                },
            }, events.append)
            assert executed["error"] is None
            assert executed["result"]["result"] == 42
            assert any(event["type"] == "kernel_status" for event in events)
            status = await runtime.handle({"id": "status", "method": "kernel_status", "params": {"workspace_id": "workspace-1"}}, events.append)
            assert status["result"]["status"] == "ready"
            reset = await runtime.handle({"id": "reset", "method": "kernel_reset", "params": {"workspace_id": "workspace-1"}}, events.append)
            assert reset["result"]["reset"] is True
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_runtime_rpc_rejects_unsafe_or_missing_execution_params(tmp_path: Path) -> None:
    async def scenario() -> None:
        runtime = WorkerRuntime(idle_seconds=300)
        try:
            response = await runtime.handle({
                "id": "bad",
                "method": "kernel_execute",
                "params": {"workspace_id": "../escape", "database_path": str(tmp_path / "missing.duckdb")},
            }, lambda _: None)
            assert response["result"] is None
            assert response["error"]["code"] == "invalid_params"
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())
