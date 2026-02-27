from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services.execution_config import load_execution_runtime_config
from app.v1.api import runtime as runtime_api


@pytest.fixture(autouse=True)
def _force_local_jupyter_provider(monkeypatch):
    load_execution_runtime_config.cache_clear()
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")
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

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "reset_workspace_kernel", fake_reset)

    response = await runtime_api.reset_workspace_kernel_runtime(
        workspace_id="ws-4",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.workspace_id == "ws-4"
    assert response.reset is True
