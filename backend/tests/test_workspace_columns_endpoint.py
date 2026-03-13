from types import SimpleNamespace

import duckdb
import pytest
from fastapi import HTTPException

from app.v1.api import runtime as runtime_api


def _patch_command_turn_persistence(monkeypatch):
    async def fake_resolve_or_create_command_conversation(
        *,
        session,
        principal_id,
        workspace_id,
        conversation_id,
        command_text,
    ):
        _ = (session, principal_id, conversation_id, command_text)
        return SimpleNamespace(id="conv-test", workspace_id=workspace_id, title="New Conversation")

    async def fake_persist_command_turn(
        *,
        session,
        conversation,
        command_text,
        command_name,
        command_output,
        command_result_type,
        command_result,
        truncated,
    ):
        _ = (
            session,
            conversation,
            command_text,
            command_name,
            command_output,
            command_result_type,
            command_result,
            truncated,
        )
        return "turn-test"

    monkeypatch.setattr(
        runtime_api,
        "_resolve_or_create_command_conversation",
        fake_resolve_or_create_command_conversation,
    )
    monkeypatch.setattr(runtime_api, "_persist_command_turn", fake_persist_command_turn)


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

    async def fake_get_workspace_columns_via_kernel(workspace_id):
        assert workspace_id == "ws-1"
        return [
            {"table_name": "sales", "column_name": "id", "dtype": "INTEGER"},
            {"table_name": "sales", "column_name": "amount", "dtype": "DOUBLE"},
            {"table_name": "sales", "column_name": "city", "dtype": "VARCHAR"},
        ]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "get_workspace_columns_via_kernel", fake_get_workspace_columns_via_kernel)
    _patch_command_turn_persistence(monkeypatch)

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
async def test_workspace_columns_endpoint_returns_explicit_error_when_kernel_is_inactive(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-columns-kernel-missing"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    async def fake_get_workspace_columns_via_kernel(_workspace_id):
        raise RuntimeError(
            "Loading workspace columns requires an active workspace kernel because Inquira now "
            "reuses the kernel-owned DuckDB connections for workspace data and artifacts. Start "
            "or restart the workspace kernel, wait for Kernel Ready, then try again."
        )

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "get_workspace_columns_via_kernel", fake_get_workspace_columns_via_kernel)

    with pytest.raises(HTTPException) as exc:
        await runtime_api.get_workspace_columns(
            workspace_id="ws-1",
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 409
    assert "active workspace kernel" in str(exc.value.detail).lower()


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
    _patch_command_turn_persistence(monkeypatch)

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
    assert response.conversation_id == "conv-test"
    assert response.turn_id == "turn-test"


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
    _patch_command_turn_persistence(monkeypatch)

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
    assert response.conversation_id == "conv-test"
    assert response.turn_id == "turn-test"


@pytest.mark.asyncio
async def test_workspace_command_execute_unique_supports_quoted_and_legacy_bracket_column_refs(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-commands-special-columns"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute('CREATE TABLE sales ("Match ID" INTEGER, amount DOUBLE)')
        con.execute('INSERT INTO sales VALUES (1, 10.0), (1, 20.0), (2, 30.0)')
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    _patch_command_turn_persistence(monkeypatch)

    quoted_payload = runtime_api.CommandExecuteRequest(text='/unique sales."Match ID"')
    quoted_response = await runtime_api.execute_workspace_slash_command(
        workspace_id="ws-4",
        payload=quoted_payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )
    assert quoted_response.name == "unique"
    assert quoted_response.result_type == "table"
    assert quoted_response.result is not None
    quoted_rows = quoted_response.result.get("data") or []
    assert len(quoted_rows) >= 1
    assert all(row["distinct_count"] == 2 for row in quoted_rows)
    assert quoted_response.conversation_id == "conv-test"
    assert quoted_response.turn_id == "turn-test"

    bracket_payload = runtime_api.CommandExecuteRequest(text='/unique sales["Match ID"]')
    bracket_response = await runtime_api.execute_workspace_slash_command(
        workspace_id="ws-5",
        payload=bracket_payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )
    assert bracket_response.name == "unique"
    assert bracket_response.result_type == "table"
    assert bracket_response.result is not None
    bracket_rows = bracket_response.result.get("data") or []
    assert len(bracket_rows) >= 1
    assert all(row["distinct_count"] == 2 for row in bracket_rows)
    assert bracket_response.conversation_id == "conv-test"
    assert bracket_response.turn_id == "turn-test"


@pytest.mark.asyncio
async def test_workspace_command_execute_unique_supports_unquoted_spaced_column_ref(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-commands-special-columns-unquoted"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute('CREATE TABLE sales ("Match ID" INTEGER, amount DOUBLE)')
        con.execute('INSERT INTO sales VALUES (1, 10.0), (1, 20.0), (2, 30.0)')
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    _patch_command_turn_persistence(monkeypatch)

    unquoted_payload = runtime_api.CommandExecuteRequest(text="/unique sales.Match ID")
    unquoted_response = await runtime_api.execute_workspace_slash_command(
        workspace_id="ws-6",
        payload=unquoted_payload,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )
    assert unquoted_response.name == "unique"
    assert unquoted_response.result_type == "table"
    assert unquoted_response.result is not None
    unquoted_rows = unquoted_response.result.get("data") or []
    assert len(unquoted_rows) >= 1
    assert all(row["distinct_count"] == 2 for row in unquoted_rows)
    assert unquoted_response.conversation_id == "conv-test"
    assert unquoted_response.turn_id == "turn-test"


@pytest.mark.asyncio
async def test_workspace_command_execute_persists_error_turn_when_command_fails(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-commands-error-turn"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    try:
        con.execute('CREATE TABLE sales ("Match ID" INTEGER, amount DOUBLE)')
        con.execute('INSERT INTO sales VALUES (1, 10.0), (1, 20.0), (2, 30.0)')
    finally:
        con.close()

    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return workspace

    persisted_payloads = []

    async def fake_resolve_or_create_command_conversation(
        *,
        session,
        principal_id,
        workspace_id,
        conversation_id,
        command_text,
    ):
        _ = (session, principal_id, workspace_id, conversation_id, command_text)
        return SimpleNamespace(id="conv-error", workspace_id=workspace_id, title="New Conversation")

    async def fake_persist_command_turn(
        *,
        session,
        conversation,
        command_text,
        command_name,
        command_output,
        command_result_type,
        command_result,
        truncated,
    ):
        persisted_payloads.append(
            {
                "session": session,
                "conversation": conversation,
                "command_text": command_text,
                "command_name": command_name,
                "command_output": command_output,
                "command_result_type": command_result_type,
                "command_result": command_result,
                "truncated": truncated,
            }
        )
        return "turn-error"

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(
        runtime_api,
        "_resolve_or_create_command_conversation",
        fake_resolve_or_create_command_conversation,
    )
    monkeypatch.setattr(runtime_api, "_persist_command_turn", fake_persist_command_turn)

    payload = runtime_api.CommandExecuteRequest(text="/unique sales.unknown_column")
    with pytest.raises(HTTPException) as exc:
        await runtime_api.execute_workspace_slash_command(
            workspace_id="ws-7",
            payload=payload,
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 400
    assert "could not resolve" in str(exc.value.detail).lower()
    assert len(persisted_payloads) == 1
    assert persisted_payloads[0]["command_result_type"] == "error"
    assert "command failed" in str(persisted_payloads[0]["command_output"]).lower()
