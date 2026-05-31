import asyncio
from datetime import UTC, datetime, timedelta
from queue import Empty as QueueEmpty
from types import SimpleNamespace

import pytest

from app.services.workspace_kernel_manager import (
    WorkspaceKernelManager,
    WorkspaceKernelSession,
)
from app.services.jupyter_message_parser import ParsedExecutionOutput


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
async def test_touch_session_throttles_runtime_lease_renewal(monkeypatch):
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-lease", "/tmp/ws-lease.duckdb")
    now = datetime.now(UTC)
    session.runtime_lease_owner_token = "kernel:ws-lease:test"
    session.runtime_lease_expires_at = now + timedelta(minutes=30)
    session.runtime_lease_renew_after = now + timedelta(minutes=5)
    renewals = {"count": 0}

    async def fake_renew(current_session):
        renewals["count"] += 1
        current_session.runtime_lease_expires_at = datetime.now(UTC) + timedelta(minutes=30)
        current_session.runtime_lease_renew_after = datetime.now(UTC) + timedelta(minutes=5)
        return True

    monkeypatch.setattr(manager, "_renew_runtime_lease", fake_renew)

    await manager._touch_session(session)
    await manager._touch_session(session)
    assert renewals["count"] == 0

    session.runtime_lease_renew_after = datetime.now(UTC) - timedelta(seconds=1)
    await manager._touch_session(session)
    await manager._touch_session(session)

    assert renewals["count"] == 1


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
async def test_execute_request_tolerates_transient_iopub_empty_events():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-io", "/tmp/ws-io.duckdb")

    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        def execute(self, code, store_history=True, stop_on_error=True):
            _ = (code, store_history, stop_on_error)
            return "msg-1"

        async def get_iopub_msg(self, timeout=1):
            _ = timeout
            self.calls += 1
            if self.calls == 1:
                raise QueueEmpty()
            if self.calls == 2:
                return {
                    "parent_header": {"msg_id": "msg-1"},
                    "msg_type": "execute_result",
                    "content": {"data": {"text/plain": "1"}},
                }
            return {
                "parent_header": {"msg_id": "msg-1"},
                "msg_type": "status",
                "content": {"execution_state": "idle"},
            }

    fake_client = FakeClient()
    session.client = fake_client

    parsed = await manager._execute_request(session, "1", iopub_idle_timeout=2)

    assert parsed.error is None
    assert fake_client.calls >= 3


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
async def test_execute_on_session_prefers_identifier_probe_for_selected_variable():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-1", "/tmp/a.duckdb")
    calls = {"count": 0}

    async def fake_execute_request(current_session, code):
        _ = current_session
        calls["count"] += 1
        parsed = ParsedExecutionOutput()
        if calls["count"] == 1:
            assert code == "top_batsmen_df"
            return parsed
        if calls["count"] == 2:
            assert "_inquira_identifier = 'top_batsmen_df'" in code
            parsed.result = {"columns": ["a"], "data": [{"a": 1}]}
            parsed.result_type = "DataFrame"
            return parsed
        raise AssertionError("Generic fallback probe should not run when identifier probe succeeds")

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "top_batsmen_df")

    assert calls["count"] == 2
    assert payload["result_type"] == "DataFrame"
    assert payload["result_kind"] == "dataframe"
    assert payload["result_name"] == "top_batsmen_df"
    assert payload["result"] == {"columns": ["a"], "data": [{"a": 1}]}


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
        assert "_inquira_payload" in code
        parsed.result = None
        parsed.result_type = None
        return parsed

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "top_batsmen")

    assert payload["result_kind"] in {"scalar", "none"}
    if payload["result_kind"] == "scalar":
        assert payload["result_name"] == "top_batsmen"


@pytest.mark.asyncio
async def test_execute_on_session_returns_empty_artifacts_when_probe_fails():
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
            parsed.result = None
            parsed.result_type = None
            return parsed
        raise RuntimeError("exports probe failed")

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    payload = await manager._execute_on_session(session, "x = 1")

    assert payload["result"] == {"ok": True}
    assert payload["variables"]["dataframes"] == {}
    assert payload["artifacts"] == []


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
        if "conn.close()" in code:
            events.append("cleanup_code")
        return ParsedExecutionOutput()

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]

    await manager._shutdown_session(session)

    assert events == ["cleanup_code", "stop_channels", "shutdown_kernel"]


@pytest.mark.asyncio
async def test_shutdown_session_releases_runtime_lease():
    manager = WorkspaceKernelManager(idle_minutes=30)
    session = _session("ws-clean", "/tmp/a.duckdb")
    session.runtime_lease_owner_token = "owner-1"
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
        _ = (current_session, code)
        return ParsedExecutionOutput()

    async def fake_release(current_session):
        assert current_session is session
        events.append("release_lease")

    manager._execute_request = fake_execute_request  # type: ignore[method-assign]
    manager._release_runtime_lease = fake_release  # type: ignore[method-assign]

    await manager._shutdown_session(session)

    assert events == ["stop_channels", "shutdown_kernel", "release_lease"]


@pytest.mark.asyncio
async def test_bootstrap_workspace_creates_missing_workspace_duckdb(tmp_path):
    manager = WorkspaceKernelManager(idle_minutes=30)
    workspace_db = tmp_path / "ws-new" / "workspace.duckdb"
    session = WorkspaceKernelSession(
        workspace_id="ws-new",
        workspace_duckdb_path=str(workspace_db),
        manager=SimpleNamespace(),
        client=SimpleNamespace(),
    )

    async def fake_execute_on_session(current_session, code):
        _ = current_session
        assert str(workspace_db.as_posix()) in code
        return {"success": True}

    manager._execute_on_session = fake_execute_on_session  # type: ignore[method-assign]

    assert not workspace_db.exists()
    await manager._bootstrap_workspace(session)
    assert workspace_db.exists()


@pytest.mark.asyncio
async def test_bootstrap_workspace_exports_figure_payload_in_run_envelope(tmp_path):
    manager = WorkspaceKernelManager(idle_minutes=30)
    workspace_db = tmp_path / "ws-fig" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()
    session = WorkspaceKernelSession(
        workspace_id="ws-fig",
        workspace_duckdb_path=str(workspace_db),
        manager=SimpleNamespace(),
        client=SimpleNamespace(),
    )

    captured: dict[str, str] = {}

    async def fake_execute_on_session(current_session, code):
        _ = current_session
        captured["code"] = code
        return {"success": True}

    manager._execute_on_session = fake_execute_on_session  # type: ignore[method-assign]

    await manager._bootstrap_workspace(session)

    bootstrap_code = captured.get("code", "")
    assert "payload=None, status='ready', error=None" in bootstrap_code
    assert "'payload': payload" in bootstrap_code
    assert "kind='figure'" in bootstrap_code
    assert "payload = {'figure': fig_payload, 'title': title, 'insight': insight}" in bootstrap_code
    assert "_inquira_replace_run_export(active_run, 'scalar'" in bootstrap_code
    assert "storage_path.write_text(_json.dumps(payload, default=str), encoding='utf-8')" in bootstrap_code
    assert "_pd_display.set_option('display.max_rows', 1000)" in bootstrap_code
    assert "_pd_display.set_option('display.max_columns', 20)" in bootstrap_code
    assert "_pd_display.set_option('display.large_repr', 'truncate')" in bootstrap_code
