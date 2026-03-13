from types import SimpleNamespace

import pytest

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_schema_endpoint_uses_kernel_schema_when_dataset_row_missing(monkeypatch, tmp_path):
    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path=str(tmp_path / "workspace.duckdb"))

    async def fake_get_dataset(**_kwargs):
        return None

    async def fake_schema_via_kernel(*, workspace_id, table_name, allow_sample_values):
        assert workspace_id == "ws-1"
        assert table_name == "deliveries__9fda06be"
        assert allow_sample_values is False
        return [
            {"name": "id", "dtype": "INTEGER", "description": "", "samples": [], "aliases": []},
            {"name": "team", "dtype": "VARCHAR", "description": "", "samples": [], "aliases": []},
        ]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api, "get_workspace_table_schema_via_kernel", fake_schema_via_kernel)

    response = await runtime_api.get_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="deliveries__9fda06be",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "deliveries__9fda06be"
    assert len(response.columns) == 2


@pytest.mark.asyncio
async def test_schema_endpoint_falls_back_to_kernel_schema_when_saved_schema_is_invalid(
    monkeypatch, tmp_path
):
    workspace_dir = tmp_path / "ws_invalid_schema"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    bad_schema_path = workspace_dir / "meta" / "ball_by_ball_ipl__5c3affa_schema.json"
    bad_schema_path.parent.mkdir(parents=True, exist_ok=True)
    bad_schema_path.write_text("{not-valid-json", encoding="utf-8")

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path=str(workspace_dir / "workspace.duckdb"))

    async def fake_get_dataset(**_kwargs):
        return SimpleNamespace(schema_path=str(bad_schema_path))

    async def fake_schema_via_kernel(*, workspace_id, table_name, allow_sample_values):
        assert workspace_id == "ws-1"
        assert table_name == "ball_by_ball_ipl__5c3affa"
        assert allow_sample_values is False
        return [
            {"name": "Batter", "dtype": "VARCHAR", "description": "", "samples": [], "aliases": []},
            {"name": "runs", "dtype": "INTEGER", "description": "", "samples": [], "aliases": []},
        ]

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api, "get_workspace_table_schema_via_kernel", fake_schema_via_kernel)

    response = await runtime_api.get_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="ball_by_ball_ipl__5c3affa",
        session=object(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert response.table_name == "ball_by_ball_ipl__5c3affa"
    assert len(response.columns) == 2
