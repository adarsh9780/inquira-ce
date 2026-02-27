from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.execution_config import load_execution_runtime_config
from app.v1.api import runtime as runtime_api


@pytest.fixture(autouse=True)
def _force_local_jupyter_provider(monkeypatch):
    # Runtime API tests assert workspace-scoped execution wiring.
    load_execution_runtime_config.cache_clear()
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_jupyter")
    yield
    load_execution_runtime_config.cache_clear()


def test_execute_endpoint_requires_auth_cookie():
    client = TestClient(app)
    response = client.post(
        "/api/v1/workspaces/ws-1/execute",
        json={"code": "result = 1", "timeout": 5},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_execute_workspace_cannot_query_table_from_other_workspace(monkeypatch, tmp_path):
    ws_a_dir = tmp_path / "workspace_a"
    ws_a_dir.mkdir(parents=True, exist_ok=True)
    db_a = ws_a_dir / "workspace.duckdb"
    db_a.touch()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return SimpleNamespace(duckdb_path=str(db_a))

    async def fake_execute_code(
        code,
        timeout,
        working_dir=None,
        workspace_id=None,
        workspace_duckdb_path=None,
    ):
        _ = (timeout, working_dir)
        assert workspace_id == "workspace-a"
        assert workspace_duckdb_path == str(db_a)
        if "table_b" in code:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Catalog Error: Table with name table_b does not exist",
                "error": "Catalog Error: Table with name table_b does not exist",
                "result": None,
                "result_type": None,
            }
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

    response = await runtime_api.execute_workspace_code(
        workspace_id="workspace-a",
        payload=runtime_api.ExecuteRequest(
            code='result = conn.sql("SELECT * FROM table_b").fetchall()',
            timeout=10,
        ),
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.success is False
    assert "table_b" in ((response.error or "") + (response.stderr or "")).lower()
