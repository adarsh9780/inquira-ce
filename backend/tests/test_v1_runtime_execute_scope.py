from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services.execution_config import load_execution_runtime_config
from app.v1.api import runtime as runtime_api


@pytest.fixture(autouse=True)
def _force_local_jupyter_provider(monkeypatch):
    load_execution_runtime_config.cache_clear()
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")
    monkeypatch.setenv("INQUIRA_TERMINAL_ENABLE", "true")
    yield
    load_execution_runtime_config.cache_clear()


@pytest.mark.asyncio
async def test_execute_workspace_code_passes_workspace_context(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws1"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return workspace

    captured = {}

    async def fake_execute_code_with_workspace(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        captured["code"] = code
        captured["timeout"] = timeout
        captured["working_dir"] = working_dir
        captured["workspace_id"] = workspace_id
        captured["workspace_duckdb_path"] = workspace_duckdb_path
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code_with_workspace)

    payload = runtime_api.ExecuteRequest(code="result = conn.sql('select 1').fetchall()", timeout=30)
    current_user = SimpleNamespace(id="user-1")

    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=payload,
        session=object(),
        current_user=current_user,
    )

    assert response.success is True
    assert captured["code"] == "result = conn.sql('select 1').fetchall()"
    assert captured["working_dir"] == str(Path(duckdb_path).parent)
    assert captured["workspace_id"] == "ws-1"
    assert captured["workspace_duckdb_path"] == str(duckdb_path)


@pytest.mark.asyncio
async def test_execute_workspace_code_returns_upstream_result(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws2"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_execute_code(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        _ = (code, timeout, working_dir, workspace_id, workspace_duckdb_path)
        return {
            "success": False,
            "stdout": "",
            "stderr": "boom",
            "error": "boom",
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code)

    payload = runtime_api.ExecuteRequest(code='print("x")', timeout=30)
    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.success is False
    assert response.error == "boom"


@pytest.mark.asyncio
async def test_workspace_dataframe_artifact_rows_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws5"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_get_rows(workspace_id: str, artifact_id: str, offset: int, limit: int):
        assert workspace_id == "ws-5"
        assert artifact_id == "art-1"
        assert offset == 0
        assert limit == 1000
        return {
            "artifact_id": "art-1",
            "name": "summary",
            "row_count": 2000,
            "columns": ["a"],
            "rows": [{"a": 1}],
            "offset": 0,
            "limit": 1000,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "get_workspace_dataframe_rows", fake_get_rows)

    response = await runtime_api.get_workspace_dataframe_artifact_rows(
        workspace_id="ws-5",
        artifact_id="art-1",
        offset=0,
        limit=1000,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.artifact_id == "art-1"
    assert response.row_count == 2000
    assert response.rows == [{"a": 1}]


@pytest.mark.asyncio
async def test_workspace_kernel_status_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws3"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_status(workspace_id: str):
        assert workspace_id == "ws-3"
        return "ready"

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "get_workspace_kernel_status", fake_status)

    response = await runtime_api.get_workspace_kernel_runtime_status(
        workspace_id="ws-3",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-3"
    assert response.status == "ready"


@pytest.mark.asyncio
async def test_workspace_kernel_reset_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws4"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-4"
        return True

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-4"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.reset_workspace_kernel_runtime(
        workspace_id="ws-4",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-4"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_kernel_interrupt_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws6"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_interrupt(workspace_id: str):
        assert workspace_id == "ws-6"
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "interrupt_workspace_kernel", fake_interrupt)

    response = await runtime_api.interrupt_workspace_kernel_runtime(
        workspace_id="ws-6",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-6"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_terminal_execute_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws7"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    captured = {}

    async def fake_run_terminal_command(*, user_id, workspace_id, command, workspace_dir, cwd, timeout):
        captured["user_id"] = user_id
        captured["workspace_id"] = workspace_id
        captured["command"] = command
        captured["workspace_dir"] = workspace_dir
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return {
            "stdout": "ok\n",
            "stderr": "",
            "exit_code": 0,
            "cwd": workspace_dir,
            "shell": "/bin/bash",
            "platform": "Darwin",
            "timed_out": False,
            "persistent": True,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "run_workspace_terminal_command", fake_run_terminal_command)

    response = await runtime_api.execute_workspace_terminal_command(
        workspace_id="ws-7",
        payload=runtime_api.TerminalExecuteRequest(command="pwd", cwd=None, timeout=90),
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.exit_code == 0
    assert response.stdout == "ok\n"
    assert captured["user_id"] == "user-1"
    assert captured["workspace_id"] == "ws-7"
    assert captured["command"] == "pwd"
    assert captured["workspace_dir"] == str(workspace_dir)
    assert captured["cwd"] is None
    assert captured["timeout"] == 90


@pytest.mark.asyncio
async def test_workspace_terminal_session_reset_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws9"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_stop_terminal(*, user_id, workspace_id):
        assert user_id == "user-1"
        assert workspace_id == "ws-9"
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "stop_workspace_terminal_session", fake_stop_terminal)

    response = await runtime_api.reset_workspace_terminal_session(
        workspace_id="ws-9",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-9"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_terminal_execute_enforces_allowlist_policy(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws10"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    def fake_load_runtime_config():
        return SimpleNamespace(
            terminal_enabled=True,
            terminal_command_allowlist=["pwd"],
            terminal_command_denylist=[],
        )

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "load_execution_runtime_config", fake_load_runtime_config)

    with pytest.raises(runtime_api.HTTPException) as exc:
        await runtime_api.execute_workspace_terminal_command(
            workspace_id="ws-10",
            payload=runtime_api.TerminalExecuteRequest(command="ls -la", cwd=None, timeout=30),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workspace_kernel_restart_endpoint(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws7"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-7"
        return True

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-7"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.restart_workspace_kernel_runtime(
        workspace_id="ws-7",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-7"
    assert response.reset is True


@pytest.mark.asyncio
async def test_workspace_kernel_restart_warms_when_no_existing_session(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws8"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_reset(workspace_id: str):
        assert workspace_id == "ws-8"
        return False

    async def fake_bootstrap_workspace_runtime(*, workspace_id, workspace_duckdb_path, progress_callback=None):
        assert workspace_id == "ws-8"
        assert workspace_duckdb_path == str(duckdb_path)
        assert progress_callback is None
        return True

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)
    monkeypatch.setattr(runtime_api, "bootstrap_workspace_runtime", fake_bootstrap_workspace_runtime)

    response = await runtime_api.restart_workspace_kernel_runtime(
        workspace_id="ws-8",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-8"
    assert response.reset is True
