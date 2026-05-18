from types import SimpleNamespace

import pytest

from app.v1.api import runtime as runtime_api


class _TrackingSession:
    def __init__(self) -> None:
        self.commits = 0
        self._in_transaction = True

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def commit(self) -> None:
        self.commits += 1
        self._in_transaction = False


@pytest.mark.asyncio
async def test_workspace_columns_route_releases_db_before_kernel(monkeypatch, tmp_path):
    session = _TrackingSession()
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(_session, principal_id, workspace_id):
        assert _session is session
        assert principal_id == "user-1"
        assert workspace_id == "ws-1"
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_workspace_columns_via_kernel(workspace_id):
        assert workspace_id == "ws-1"
        assert session.commits == 1
        assert session.in_transaction() is False
        return [{"table_name": "orders", "column_name": "id", "dtype": "BIGINT"}]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "get_workspace_columns_via_kernel", fake_get_workspace_columns_via_kernel)

    response = await runtime_api.get_workspace_columns(
        workspace_id="ws-1",
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.columns == [{"table_name": "orders", "column_name": "id", "dtype": "BIGINT"}]


@pytest.mark.asyncio
async def test_execute_route_releases_db_before_kernel_execution(monkeypatch, tmp_path):
    session = _TrackingSession()
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(_session, principal_id, workspace_id):
        assert _session is session
        assert principal_id == "user-1"
        assert workspace_id == "ws-1"
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_execute_workspace_code_impl(*, workspace_id, workspace_duckdb_path, payload):
        assert workspace_id == "ws-1"
        assert workspace_duckdb_path == str(duckdb_path)
        assert payload.code == "print(1)"
        assert session.commits == 1
        assert session.in_transaction() is False
        return runtime_api.ExecuteResponse(success=True, stdout="1\n")

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api, "_execute_workspace_code_impl", fake_execute_workspace_code_impl)

    response = await runtime_api.execute_workspace_code(
        workspace_id="ws-1",
        payload=runtime_api.ExecuteRequest(code="print(1)", timeout=1),
        session=session,
        current_user=SimpleNamespace(id="user-1", username="alice"),
    )

    assert response.success is True
    assert response.stdout == "1\n"


@pytest.mark.asyncio
async def test_dataset_schema_route_releases_db_before_kernel_fallback(monkeypatch):
    session = _TrackingSession()

    async def fake_require_workspace_access(_session, principal_id, workspace_id):
        assert _session is session
        assert principal_id == "user-1"
        assert workspace_id == "ws-1"
        return SimpleNamespace()

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        assert workspace_id == "ws-1"
        assert table_name == "orders"
        return None

    async def fake_get_workspace_table_schema_via_kernel(*, workspace_id, table_name, allow_sample_values):
        assert workspace_id == "ws-1"
        assert table_name == "orders"
        assert allow_sample_values is False
        assert session.commits == 1
        assert session.in_transaction() is False
        return [{"name": "order_id", "dtype": "BIGINT"}]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_for_workspace_table)
    monkeypatch.setattr(runtime_api, "get_workspace_table_schema_via_kernel", fake_get_workspace_table_schema_via_kernel)

    response = await runtime_api.get_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="orders",
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "orders"
    assert response.columns == [{"name": "order_id", "dtype": "BIGINT"}]
