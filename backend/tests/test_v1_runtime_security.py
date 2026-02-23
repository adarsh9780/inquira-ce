from types import SimpleNamespace

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.execution_config import load_execution_runtime_config
from app.v1.api import runtime as runtime_api


@pytest.fixture(autouse=True)
def _force_local_subprocess_provider(monkeypatch):
    # Runtime API tests assert DuckDB workspace behavior, not safe-runner internals.
    load_execution_runtime_config.cache_clear()
    monkeypatch.setenv("INQUIRA_EXECUTION_PROVIDER", "local_subprocess")
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
    ws_b_dir = tmp_path / "workspace_b"
    ws_a_dir.mkdir(parents=True, exist_ok=True)
    ws_b_dir.mkdir(parents=True, exist_ok=True)
    db_a = ws_a_dir / "workspace.duckdb"
    db_b = ws_b_dir / "workspace.duckdb"

    con_a = duckdb.connect(str(db_a))
    con_a.execute("CREATE TABLE table_a AS SELECT 1 AS id")
    con_a.close()

    con_b = duckdb.connect(str(db_b))
    con_b.execute("CREATE TABLE table_b AS SELECT 2 AS id")
    con_b.close()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return SimpleNamespace(duckdb_path=str(db_a))

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

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
