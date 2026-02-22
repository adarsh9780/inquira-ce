from types import SimpleNamespace
from pathlib import Path

import duckdb
import pytest

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_execute_workspace_code_injects_workspace_duckdb_connection(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws1"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return workspace

    captured = {}

    async def fake_execute_code(code, timeout, working_dir=None):
        captured["code"] = code
        captured["timeout"] = timeout
        captured["working_dir"] = working_dir
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
        }

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code)

    payload = runtime_api.ExecuteRequest(code="result = conn.sql('select 1').fetchall()", timeout=30)
    current_user = SimpleNamespace(id="user-1")

    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=payload,
        session=object(),
        current_user=current_user,
    )

    assert response.success is True
    assert "conn = duckdb.connect" in captured["code"]
    assert str(duckdb_path) in captured["code"]
    assert captured["working_dir"] == str(Path(duckdb_path).parent)


@pytest.mark.asyncio
async def test_execute_workspace_code_runs_query_against_workspace_duckdb(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws2"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    con.execute("CREATE TABLE orders AS SELECT 1 AS id UNION ALL SELECT 2 AS id")
    con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    payload = runtime_api.ExecuteRequest(
        code='conn.sql("SELECT COUNT(*) AS c FROM orders").fetchall()',
        timeout=30,
    )
    current_user = SimpleNamespace(id="user-1")

    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=current_user,
    )

    assert response.success is True
    assert response.error is None
