from types import SimpleNamespace

import pytest

from app.v1.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_browser_sync_strips_samples_when_privacy_mode_disabled(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()
    workspace = SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_workspace(_session, _workspace_id, _user_id):
        return workspace

    class _Result:
        def scalar_one_or_none(self):
            return None

    class _Session:
        def __init__(self):
            self.added = None

        async def execute(self, *_args, **_kwargs):
            return _Result()

        def add(self, item):
            self.added = item

        async def commit(self):
            return None

        async def refresh(self, _item):
            return None

    monkeypatch.setattr("app.v1.services.dataset_service.WorkspaceRepository.get_by_id", fake_workspace)

    session = _Session()
    user = SimpleNamespace(id="u1")

    await DatasetService.sync_browser_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        table_name="sales",
        columns=[{"name": "city", "dtype": "VARCHAR", "samples": ["NYC"]}],
        row_count=1,
        allow_sample_values=False,
    )

    assert session.added is not None
    schema_path = workspace_dir / "meta" / "sales_schema.json"
    payload = schema_path.read_text(encoding="utf-8")
    assert '"samples": []' in payload
