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
            pong = await runtime.handle(
                {"id": "ping", "method": "ping", "params": {}}, events.append
            )
            assert pong["result"]["status"] == "ready"
            executed = await runtime.handle(
                {
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
                },
                events.append,
            )
            assert executed["error"] is None
            assert executed["result"]["result"] == 42
            assert any(event["type"] == "kernel_status" for event in events)
            status = await runtime.handle(
                {
                    "id": "status",
                    "method": "kernel_status",
                    "params": {"workspace_id": "workspace-1"},
                },
                events.append,
            )
            assert status["result"]["status"] == "ready"
            reset = await runtime.handle(
                {
                    "id": "reset",
                    "method": "kernel_reset",
                    "params": {"workspace_id": "workspace-1"},
                },
                events.append,
            )
            assert reset["result"]["reset"] is True
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_runtime_rpc_rejects_unsafe_or_missing_execution_params(tmp_path: Path) -> None:
    async def scenario() -> None:
        runtime = WorkerRuntime(idle_seconds=300)
        try:
            response = await runtime.handle(
                {
                    "id": "bad",
                    "method": "kernel_execute",
                    "params": {
                        "workspace_id": "../escape",
                        "database_path": str(tmp_path / "missing.duckdb"),
                    },
                },
                lambda _: None,
            )
            assert response["result"] is None
            assert response["error"]["code"] == "invalid_params"
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_runtime_rpc_exposes_artifact_inspection_and_rows(tmp_path: Path) -> None:
    async def scenario() -> None:
        artifact = tmp_path / "data.parquet"
        connection = duckdb.connect()
        connection.execute(
            "COPY (SELECT 1 AS id UNION ALL SELECT 2) TO ? (FORMAT PARQUET)",
            [str(artifact)],
        )
        connection.close()
        runtime = WorkerRuntime()
        try:
            inspected = await runtime.handle(
                {
                    "id": "inspect",
                    "method": "artifact_inspect",
                    "params": {"artifact_path": str(artifact)},
                },
                lambda _: None,
            )
            assert inspected["error"] is None and inspected["result"]["row_count"] == 2
            rows = await runtime.handle(
                {
                    "id": "rows",
                    "method": "artifact_rows",
                    "params": {"artifact_path": str(artifact), "offset": 1, "limit": 1},
                },
                lambda _: None,
            )
            assert rows["error"] is None and rows["result"]["rows"] == [{"id": 2}]
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_runtime_rpc_exposes_schema_description_generation() -> None:
    class FakeSchemaGenerator:
        async def generate(self, params: dict) -> dict:
            assert params["table_name"] == "sales"
            return {"columns": [{"name": "amount", "description": "Booked revenue", "aliases": ["sales"]}]}

    async def scenario() -> None:
        runtime = WorkerRuntime()
        runtime.schema_generator = FakeSchemaGenerator()
        try:
            response = await runtime.handle({
                "id": "schema",
                "method": "schema_describe",
                "params": {"table_name": "sales"},
            }, lambda _: None)
            assert response["error"] is None
            assert response["result"]["columns"][0]["description"] == "Booked revenue"
        finally:
            await runtime.shutdown()

    asyncio.run(scenario())


def test_runtime_rpc_cancels_an_active_agent_request_and_interrupts_its_workspace() -> None:
    class SlowAgent:
        def __init__(self) -> None:
            self.started = asyncio.Event()

        async def analyze(self, params: dict, emit) -> dict:
            _ = params, emit
            self.started.set()
            await asyncio.Event().wait()
            raise AssertionError("cancelled analysis continued")

    class InterruptingKernels:
        def __init__(self) -> None:
            self.interrupted: list[str] = []

        async def interrupt(self, workspace_id: str) -> bool:
            self.interrupted.append(workspace_id)
            return True

        async def shutdown(self) -> None:
            return None

    async def scenario() -> None:
        runtime = WorkerRuntime()
        runtime.agent = SlowAgent()
        runtime.kernels = InterruptingKernels()
        analysis = asyncio.create_task(runtime.handle({
            "id": "analysis",
            "method": "agent_analyze",
            "params": {"workspace_id": "workspace-1"},
        }, lambda _: None))
        await runtime.agent.started.wait()

        cancelled = await runtime.handle({
            "id": "cancel",
            "method": "agent_cancel",
            "params": {"workspace_id": "workspace-1"},
        }, lambda _: None)
        response = await analysis

        assert cancelled["error"] is None
        assert cancelled["result"] == {"workspace_id": "workspace-1", "cancelled": True}
        assert response["error"]["code"] == "agent_cancelled"
        assert runtime.kernels.interrupted == ["workspace-1"]

    asyncio.run(scenario())
