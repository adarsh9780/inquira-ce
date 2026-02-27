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

    def should_not_connect(_path):
        raise AssertionError("duckdb.connect must not be called for unchanged files")

    monkeypatch.setattr(dataset_service_module.duckdb, "connect", should_not_connect)

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

    calls = {"create": 0}

    class FakeConn:
        def __init__(self):
            self._last_sql = ""

        def execute(self, sql, _params=None):
            self._last_sql = str(sql)
            if "CREATE OR REPLACE TABLE" in self._last_sql:
                calls["create"] += 1
            return self

        def fetchone(self):
            return (1,)

        def fetchall(self):
            return [("a", "INTEGER")]

        def close(self):
            return None

    monkeypatch.setattr(dataset_service_module.duckdb, "connect", lambda _path: FakeConn())

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result is existing
    assert calls["create"] == 1
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

    calls = {"read_excel": 0, "register": 0, "create": 0, "unregister": 0}

    class FakeConn:
        def __init__(self):
            self._last_sql = ""

        def register(self, name, dataframe):
            _ = dataframe
            if name == "_inquira_excel_df":
                calls["register"] += 1

        def unregister(self, name):
            if name == "_inquira_excel_df":
                calls["unregister"] += 1

        def execute(self, sql, _params=None):
            self._last_sql = str(sql)
            if "CREATE OR REPLACE TABLE" in self._last_sql and "_inquira_excel_df" in self._last_sql:
                calls["create"] += 1
            return self

        def fetchone(self):
            return (2,)

        def fetchall(self):
            return [("a", "INTEGER"), ("b", "VARCHAR")]

        def close(self):
            return None

    def fake_read_excel(path, engine=None):
        assert path == str(source)
        assert engine == "openpyxl"
        calls["read_excel"] += 1
        return [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]

    monkeypatch.setattr(dataset_service_module.pd, "read_excel", fake_read_excel)
    monkeypatch.setattr(dataset_service_module.duckdb, "connect", lambda _path: FakeConn())

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result.file_type == "xlsx"
    assert calls["read_excel"] == 1
    assert calls["register"] == 1
    assert calls["create"] == 1
    assert calls["unregister"] == 1
    assert session.committed is True
