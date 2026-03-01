import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.workspace_kernel_manager import (
    WorkspaceKernelManager,
    WorkspaceKernelSession,
)
from app.services.jupyter_message_parser import ParsedExecutionOutput


def _session(workspace_id: str, workspace_duckdb_path: str) -> WorkspaceKernelSession:
    artifact_db_path = str(Path(workspace_duckdb_path).with_name("workspace_runtime_artifacts.duckdb"))
    return WorkspaceKernelSession(
        workspace_id=workspace_id,
        workspace_duckdb_path=workspace_duckdb_path,
        manager=SimpleNamespace(),
        client=SimpleNamespace(),
        artifact_db_path=artifact_db_path,
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
async def test_interrupt_workspace_updates_status():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    session.status = "busy"
    called = {"interrupt": 0}

    async def fake_interrupt():
        called["interrupt"] += 1

    session.manager = SimpleNamespace(interrupt_kernel=fake_interrupt)
    manager._sessions["ws-1"] = session

    assert await manager.interrupt_workspace("ws-1") is True
    assert called["interrupt"] == 1
    assert session.status == "ready"


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


@pytest.mark.asyncio
async def test_execute_on_session_uses_fallback_probe_when_primary_has_no_result():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = (current_session, code)
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            parsed.stdout_parts.append("ok")
            return parsed
        parsed.result = {"columns": ["x"], "data": [{"x": 1}]}
        parsed.result_type = "DataFrame"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "df = ...")

    assert calls["count"] == 2
    assert payload["success"] is True
    assert payload["result_type"] == "DataFrame"
    assert payload["result_kind"] == "dataframe"
    assert payload["result"] == {"columns": ["x"], "data": [{"x": 1}]}


@pytest.mark.asyncio
async def test_execute_on_session_probes_scalar_result_without_overriding_scalar_payload():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = (current_session, code)
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            parsed.result = {"value": 1}
            parsed.result_type = "scalar"
            return parsed
        parsed.result = {"from_probe": 2}
        parsed.result_type = "scalar"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "1")

    assert calls["count"] == 2
    assert payload["result_type"] == "scalar"
    assert payload["result_kind"] == "scalar"
    assert payload["result"] == {"value": 1}


@pytest.mark.asyncio
async def test_execute_on_session_promotes_scalar_primary_when_probe_finds_dataframe():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = (current_session, code)
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            parsed.result = "   a\n0  1"
            parsed.result_type = "scalar"
            return parsed
        parsed.result = {"columns": ["a"], "data": [{"a": 1}]}
        parsed.result_type = "DataFrame"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "df.head()")

    assert calls["count"] == 2
    assert payload["result_type"] == "DataFrame"
    assert payload["result_kind"] == "dataframe"
    assert payload["result"] == {"columns": ["a"], "data": [{"a": 1}]}


@pytest.mark.asyncio
async def test_execute_on_session_fallback_still_runs_when_stderr_contains_warning():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = (current_session, code)
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            parsed.stderr_parts.append("FutureWarning: something changed")
            parsed.result = "   a\n0  1"
            parsed.result_type = "scalar"
            return parsed
        parsed.result = {"columns": ["a"], "data": [{"a": 1}]}
        parsed.result_type = "DataFrame"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "df.head()")

    assert calls["count"] == 2
    assert payload["result_type"] == "DataFrame"
    assert payload["result_kind"] == "dataframe"
    assert payload["result"] == {"columns": ["a"], "data": [{"a": 1}]}


@pytest.mark.asyncio
async def test_execute_on_session_sets_result_name_for_identifier_dataframe_selection():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    session.bootstrap_completed = True
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = current_session
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            assert code == "top_batsmen"
            parsed.result = "text repr"
            parsed.result_type = "scalar"
            return parsed
        if calls["count"] == 2:
            # fallback probe runs before artifact sync for scalar primary results
            assert "_inquira_payload" in code
            parsed.result = None
            parsed.result_type = None
            return parsed
        assert "_bundle" in code
        parsed.result = {
            "dataframes": {
                "top_batsmen": {
                    "artifact_id": "df-1",
                    "row_count": 2,
                    "columns": ["Batter", "Total Runs"],
                    "data": [{"Batter": "A", "Total Runs": 1}],
                }
            },
            "figures": {},
            "scalars": {},
        }
        parsed.result_type = "scalar"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "top_batsmen")

    assert payload["result_kind"] == "dataframe"
    assert payload["result_name"] == "top_batsmen"


@pytest.mark.asyncio
async def test_get_dataframe_rows_reads_paginated_chunk(tmp_path):
    manager = WorkspaceKernelManager(idle_minutes=30)
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()
    session = _session("ws-2", str(workspace_db))
    session.artifact_registry = {
        "artifact-1": {
            "kind": "dataframe",
            "name": "summary",
            "table_name": "df_summary",
            "row_count": 3,
        }
    }
    manager._sessions["ws-2"] = session

    async def fake_execute_request(current_session, code):
        _ = current_session
        assert "SELECT * FROM \"df_summary\" LIMIT 2 OFFSET 1" in code
        parsed = ParsedExecutionOutput()
        parsed.result = {"columns": ["a"], "rows": [{"a": 2}, {"a": 3}]}
        parsed.result_type = "scalar"
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    rows = await manager.get_dataframe_rows(
        workspace_id="ws-2",
        artifact_id="artifact-1",
        offset=1,
        limit=2,
    )

    assert rows is not None
    assert rows["artifact_id"] == "artifact-1"
    assert rows["name"] == "summary"
    assert rows["row_count"] == 3
    assert rows["rows"] == [{"a": 2}, {"a": 3}]


def test_coerce_variable_bundle_accepts_json_string_payload():
    bundle_json = (
        '{"dataframes":{"df":{"artifact_id":"a1","row_count":1,"data":[{"x":1}]}},"figures":{"fig":{"data":[],"layout":{}}},"scalars":{"n":1}}'
    )
    bundle = WorkspaceKernelManager._coerce_variable_bundle(bundle_json)

    assert bundle["dataframes"]["df"]["artifact_id"] == "a1"
    assert bundle["figures"]["fig"]["layout"] == {}
    assert bundle["scalars"]["n"] == 1


@pytest.mark.asyncio
async def test_execute_on_session_surfaces_artifact_sync_error():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-3", "/tmp/a.duckdb")
    session.bootstrap_completed = True
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = (current_session, code)
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            parsed.result = {"ok": True}
            parsed.result_type = "scalar"
            return parsed
        if calls["count"] == 2:
            # fallback probe for scalar primary
            parsed.result = None
            parsed.result_type = None
            return parsed
        raise RuntimeError("artifact sync failed")

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "x = 1")

    assert payload["result"] == {"ok": True}
    assert payload["variables"]["dataframes"] == {}
    assert payload["variables"]["figures"] == {}
    assert payload["variables"]["scalars"]["_artifact_sync_error"] == "artifact sync failed"


@pytest.mark.asyncio
async def test_shutdown_session_attempts_kernel_resource_cleanup_before_shutdown():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-clean", "/tmp/a.duckdb")
    events: list[str] = []

    class FakeClient:
        def stop_channels(self):
            events.append("stop_channels")

    class FakeKernelManager:
        async def shutdown_kernel(self, now=True):
            _ = now
            events.append("shutdown_kernel")

    session.client = FakeClient()
    session.manager = FakeKernelManager()

    async def fake_execute_request(current_session, code):
        _ = current_session
        if "artifact_conn.close()" in code and "conn.close()" in code:
            events.append("cleanup_code")
        return ParsedExecutionOutput()

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    await manager._shutdown_session(session)

    assert events == ["cleanup_code", "stop_channels", "shutdown_kernel"]
