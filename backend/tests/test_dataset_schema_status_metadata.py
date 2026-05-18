from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.v1.api import datasets as datasets_api
from app.v1.api import runtime as runtime_api
from app.v1.schemas.dataset import DatasetResponse
from app.v1.services.dataset_service import DatasetService
from app.v1.services import dataset_service as dataset_service_module


def _migration_config(db_path: Path, db_role: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = db_role
    return cfg


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, existing=None):
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


def test_workspace_dataset_migration_adds_schema_status_columns(tmp_path) -> None:
    db_path = tmp_path / "appdata_v1.db"
    command.upgrade(_migration_config(db_path, "appdata"), "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        dataset_columns = {column["name"] for column in inspector.get_columns("v1_workspace_datasets")}
        assert {"schema_status", "schema_error_message", "schema_updated_at"}.issubset(dataset_columns)
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_add_dataset_defaults_schema_status_to_queued(monkeypatch, tmp_path):
    source = tmp_path / "demo.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.touch()
    workspace = SimpleNamespace(duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="u1")
    session = _Session(existing=None)

    async def fake_workspace(_session, _workspace_id, _user_id):
        return workspace

    async def fake_ensure_kernel(workspace_id, operation_name):
        assert workspace_id == "ws-1"
        assert "dataset" in operation_name.lower()

    async def fake_ingest_dataset_via_kernel(*, workspace_id, source_path, table_name, file_type):
        assert workspace_id == "ws-1"
        assert source_path == str(source)
        assert table_name == DatasetService._normalize_table_name(str(source))
        assert file_type == "csv"
        return {
            "row_count": 1,
            "columns": [{"name": "a", "dtype": "INTEGER", "description": "", "samples": []}],
        }

    monkeypatch.setattr(dataset_service_module.WorkspaceRepository, "get_by_id", fake_workspace)
    monkeypatch.setattr(dataset_service_module, "ensure_workspace_kernel_active", fake_ensure_kernel)
    monkeypatch.setattr(dataset_service_module, "ingest_workspace_dataset_via_kernel", fake_ingest_dataset_via_kernel)

    result = await DatasetService.add_dataset(
        session=session,
        user=user,
        workspace_id="ws-1",
        source_path=str(source),
    )

    assert result.schema_status == "queued"
    assert result.schema_error_message is None
    assert result.schema_updated_at is None


@pytest.mark.asyncio
async def test_dataset_list_response_includes_schema_status_fields(monkeypatch):
    timestamp = datetime(2026, 5, 18, 12, 0, 0)
    dataset = SimpleNamespace(
        id=1,
        workspace_id="ws-1",
        source_path="/tmp/demo.csv",
        table_name="demo__1234",
        row_count=10,
        file_type="csv",
        schema_status="failed",
        schema_error_message="Model timeout",
        schema_updated_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )

    async def fake_list_datasets(_session, _principal_id, _workspace_id):
        return [dataset]

    monkeypatch.setattr(datasets_api.DatasetService, "list_datasets", fake_list_datasets)

    response = await datasets_api.list_workspace_datasets(
        workspace_id="ws-1",
        session=SimpleNamespace(),
        current_user=SimpleNamespace(id="user-1"),
    )

    item = response.datasets[0]
    assert item.schema_status == "failed"
    assert item.schema_error_message == "Model timeout"
    assert item.schema_updated_at == timestamp
    DatasetResponse(**item.model_dump())


@pytest.mark.asyncio
async def test_regenerate_schema_marks_dataset_ready(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    dataset = SimpleNamespace(
        schema_path=None,
        schema_status="queued",
        schema_error_message=None,
        schema_updated_at=None,
    )

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return dataset

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.0,
            llm_max_tokens=1024,
            llm_top_p=1.0,
            llm_top_k=0,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None, **_kwargs):
            self.api_key = api_key
            self.model = model

        def ask(self, _prompt, _schema_type, max_tokens=None):
            return SimpleNamespace(
                schemas=[SimpleNamespace(name="amount", description="Amount column")]
            )

    async def _commit():
        return None

    session = SimpleNamespace(commit=_commit)

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api.PreferencesRepository, "get_or_create", fake_get_prefs)
    monkeypatch.setattr(runtime_api.SecretStorageService, "get_api_key", lambda _user_id, provider="openrouter": "test-key")
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [{"name": "amount", "dtype": "INTEGER", "samples": [], "description": ""}],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="amounts",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Test context",
            model="google/gemini-2.5-flash",
        ),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert dataset.schema_status == "ready"
    assert dataset.schema_error_message is None
    assert dataset.schema_updated_at is not None


@pytest.mark.asyncio
async def test_regenerate_schema_marks_dataset_failed(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    dataset = SimpleNamespace(
        schema_path=None,
        schema_status="queued",
        schema_error_message=None,
        schema_updated_at=None,
    )

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return dataset

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.0,
            llm_max_tokens=1024,
            llm_top_p=1.0,
            llm_top_k=0,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None, **_kwargs):
            self.api_key = api_key
            self.model = model

        def ask(self, _prompt, _schema_type, max_tokens=None):
            raise RuntimeError("API rate limit exceeded")

    async def _commit():
        return None

    session = SimpleNamespace(commit=_commit)

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api.PreferencesRepository, "get_or_create", fake_get_prefs)
    monkeypatch.setattr(runtime_api.SecretStorageService, "get_api_key", lambda _user_id, provider="openrouter": "test-key")
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [{"name": "amount", "dtype": "INTEGER", "samples": [], "description": ""}],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    with pytest.raises(Exception):
        await runtime_api.regenerate_workspace_dataset_schema(
            workspace_id="ws-1",
            table_name="amounts",
            payload=runtime_api.RegenerateSchemaRequest(
                context="Test context",
                model="google/gemini-2.5-flash",
            ),
            session=session,
            current_user=SimpleNamespace(id="user-1"),
        )

    assert dataset.schema_status == "failed"
    assert "Failed to generate schema via LLM" in str(dataset.schema_error_message)
    assert dataset.schema_updated_at is not None
