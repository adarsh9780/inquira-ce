from types import SimpleNamespace

import duckdb
import pytest

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_schema_endpoint_uses_duckdb_fallback_when_dataset_row_missing(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    con.execute("CREATE TABLE deliveries__9fda06be AS SELECT 1 AS id, 'A' AS team")
    con.close()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(**_kwargs):
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)

    response = await runtime_api.get_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="deliveries__9fda06be",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "deliveries__9fda06be"
    assert len(response.columns) == 2


@pytest.mark.asyncio
async def test_preview_endpoint_uses_duckdb_fallback_when_dataset_row_missing(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    con.execute("CREATE TABLE deliveries__9fda06be AS SELECT 1 AS id UNION ALL SELECT 2 AS id")
    con.close()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(**_kwargs):
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)

    response = await runtime_api.get_workspace_dataset_preview(
        workspace_id="ws-1",
        table_name="deliveries__9fda06be",
        sample_type="first",
        limit=10,
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "deliveries__9fda06be"
    assert response.row_count == 2


@pytest.mark.asyncio
async def test_schema_endpoint_falls_back_to_duckdb_when_saved_schema_is_invalid(
    monkeypatch, tmp_path
):
    workspace_dir = tmp_path / "ws_invalid_schema"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"

    con = duckdb.connect(str(duckdb_path))
    con.execute("CREATE TABLE ball_by_ball_ipl__5c3affa AS SELECT 'V Kohli' AS Batter, 4 AS runs")
    con.close()

    bad_schema_path = workspace_dir / "meta" / "ball_by_ball_ipl__5c3affa_schema.json"
    bad_schema_path.parent.mkdir(parents=True, exist_ok=True)
    bad_schema_path.write_text("{not-valid-json", encoding="utf-8")

    async def fake_require_workspace_access(session, user_id, workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(**_kwargs):
        return SimpleNamespace(schema_path=str(bad_schema_path))

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)

    response = await runtime_api.get_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="ball_by_ball_ipl__5c3affa",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "ball_by_ball_ipl__5c3affa"
    assert len(response.columns) == 2
