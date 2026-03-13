from types import SimpleNamespace

import pytest

from app.v1.services.dataset_service import DatasetService
from app.v1.services import dataset_service as dataset_service_module


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, existing):
        self._existing = existing
        self.added = None
        self.committed = False

    async def execute(self, *_args, **_kwargs):
        return _Result(self._existing)

    def add(self, item):
        self.added = item

    async def commit(self):
        self.committed = True

    async def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_add_dataset_skips_ingest_when_source_unchanged(monkeypatch, tmp_path):
    source = tmp_path / "demo.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="u1")

    async def fake_workspace(_session, _workspace_id, _user_id):
        return workspace

    existing = SimpleNamespace(
        workspace_id="ws-1",
        source_path=str(source),
        source_fingerprint=DatasetService._source_fingerprint(str(source)),
        table_name="demo__abc12345",
        schema_path=str(tmp_path / "meta" / "demo_schema.json"),
        file_size=source.stat().st_size,
        source_mtime=source.stat().st_mtime,
        row_count=1,
        file_type="csv",
    )
    session = _Session(existing=existing)

    monkeypatch.setattr(
        dataset_service_module.WorkspaceRepository,
        "get_by_id",
        fake_workspace,
    )

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result is existing
    assert session.committed is False
    assert session.added is None


@pytest.mark.asyncio
async def test_add_dataset_reingests_when_source_changed(monkeypatch, tmp_path):
    source = tmp_path / "demo.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="u1")

    async def fake_workspace(_session, _workspace_id, _user_id):
        return workspace

    existing = SimpleNamespace(
        workspace_id="ws-1",
        source_path=str(source),
        source_fingerprint=DatasetService._source_fingerprint(str(source)),
        table_name="demo__abc12345",
        schema_path=str(tmp_path / "meta" / "demo_schema.json"),
        file_size=source.stat().st_size,
        source_mtime=source.stat().st_mtime - 100.0,
        row_count=1,
        file_type="csv",
    )
    session = _Session(existing=existing)
    monkeypatch.setattr(
        dataset_service_module.WorkspaceRepository,
        "get_by_id",
        fake_workspace,
    )

    calls = {"ingest": 0}

    async def fake_ensure_kernel(workspace_id, operation_name):
        assert workspace_id == "ws-1"
        assert "dataset" in operation_name.lower()

    async def fake_ingest_dataset_via_kernel(*, workspace_id, source_path, table_name, file_type):
        assert workspace_id == "ws-1"
        assert source_path == str(source)
        assert table_name == DatasetService._normalize_table_name(str(source))
        assert file_type == "csv"
        calls["ingest"] += 1
        return {
            "row_count": 1,
            "columns": [{"name": "a", "dtype": "INTEGER", "description": "", "samples": []}],
        }

    monkeypatch.setattr(dataset_service_module, "ensure_workspace_kernel_active", fake_ensure_kernel)
    monkeypatch.setattr(dataset_service_module, "ingest_workspace_dataset_via_kernel", fake_ingest_dataset_via_kernel)

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result is existing
    assert calls["ingest"] == 1
    assert session.committed is True


@pytest.mark.asyncio
async def test_add_dataset_ingests_excel_via_pandas_openpyxl(monkeypatch, tmp_path):
    source = tmp_path / "demo.xlsx"
    source.write_bytes(b"placeholder")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="u1")

    async def fake_workspace(_session, _workspace_id, _user_id):
        return workspace

    session = _Session(existing=None)
    monkeypatch.setattr(
        dataset_service_module.WorkspaceRepository,
        "get_by_id",
        fake_workspace,
    )

    calls = {"ingest": 0}

    async def fake_ensure_kernel(workspace_id, operation_name):
        assert workspace_id == "ws-1"
        assert "dataset" in operation_name.lower()

    async def fake_ingest_dataset_via_kernel(*, workspace_id, source_path, table_name, file_type):
        assert workspace_id == "ws-1"
        assert source_path == str(source)
        assert file_type == "xlsx"
        calls["ingest"] += 1
        return {
            "row_count": 2,
            "columns": [
                {"name": "a", "dtype": "INTEGER", "description": "", "samples": []},
                {"name": "b", "dtype": "VARCHAR", "description": "", "samples": []},
            ],
        }

    monkeypatch.setattr(dataset_service_module, "ensure_workspace_kernel_active", fake_ensure_kernel)
    monkeypatch.setattr(dataset_service_module, "ingest_workspace_dataset_via_kernel", fake_ingest_dataset_via_kernel)

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result.file_type == "xlsx"
    assert calls["ingest"] == 1
    assert session.committed is True
