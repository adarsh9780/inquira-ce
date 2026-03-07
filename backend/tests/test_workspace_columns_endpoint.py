from types import SimpleNamespace

import duckdb
import pytest

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_workspace_columns_endpoint_returns_catalog(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-columns"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute("CREATE TABLE sales (id INTEGER, amount DOUBLE, city VARCHAR)")
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    response = await runtime_api.get_workspace_columns(
        workspace_id="ws-1",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert isinstance(response.columns, list)
    assert {
        "table_name": "sales",
        "column_name": "id",
        "dtype": "INTEGER",
    } in response.columns
    assert {
        "table_name": "sales",
        "column_name": "amount",
        "dtype": "DOUBLE",
    } in response.columns


@pytest.mark.asyncio
async def test_workspace_command_execute_runs_shape_command(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-commands"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute("CREATE TABLE sales (id INTEGER, amount DOUBLE)")
        con.execute("INSERT INTO sales VALUES (1, 10.0), (2, 20.0), (3, 30.0)")
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    payload = runtime_api.CommandExecuteRequest(text="/shape sales")
    response = await runtime_api.execute_workspace_slash_command(
        workspace_id="ws-2",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.name == "shape"
    assert response.result_type == "table"
    assert response.result is not None
    rows = response.result.get("data") or []
    assert len(rows) == 1
    assert rows[0]["row_count"] == 3
    assert rows[0]["column_count"] == 2


@pytest.mark.asyncio
async def test_workspace_command_execute_succeeds_when_only_read_only_connect_is_allowed(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-commands-read-only"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute("CREATE TABLE sales (id INTEGER, amount DOUBLE)")
        con.execute("INSERT INTO sales VALUES (1, 10.0), (2, 20.0)")
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)

    real_connect = duckdb.connect

    def lock_sensitive_connect(*args, **kwargs):
        if kwargs.get("read_only") is not True:
            raise duckdb.IOException("Conflicting lock is held")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(runtime_api.duckdb, "connect", lock_sensitive_connect)

    payload = runtime_api.CommandExecuteRequest(text="/shape sales")
    response = await runtime_api.execute_workspace_slash_command(
        workspace_id="ws-3",
        payload=payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.name == "shape"
    assert response.result_type == "table"
    assert response.result is not None
    rows = response.result.get("data") or []
    assert len(rows) == 1
    assert rows[0]["row_count"] == 2
