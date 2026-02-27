from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.api import runtime as runtime_api
from app.services.llm_runtime_config import load_llm_runtime_config


@pytest.mark.asyncio
async def test_regenerate_schema_caps_llm_max_tokens(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    captured = {}

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=None)

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            allow_schema_sample_values=False,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str):
            captured["api_key"] = api_key
            captured["model"] = model

        def ask(self, _prompt, _schema_type, max_tokens=None):
            captured["max_tokens"] = max_tokens
            return SimpleNamespace(
                schemas=[SimpleNamespace(name="amount", description="Amount column")]
            )

    async def _commit():
        return None

    session = SimpleNamespace(commit=_commit)

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(
        runtime_api.DatasetRepository,
        "get_for_workspace_table",
        fake_get_dataset,
    )
    monkeypatch.setattr(
        runtime_api.PreferencesRepository,
        "get_or_create",
        fake_get_prefs,
    )
    monkeypatch.setattr(
        runtime_api.SecretStorageService,
        "get_api_key",
        lambda _user_id: "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "amount", "dtype": "INTEGER", "samples": [], "description": ""}
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    result = await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="amounts",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Test context",
            model="google/gemini-2.5-flash",
        ),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.table_name == "amounts"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "google/gemini-2.5-flash"
    load_llm_runtime_config.cache_clear()
    assert captured["max_tokens"] == load_llm_runtime_config().schema_max_tokens
    schema_path = Path(duckdb_path).parent / "meta" / "amounts_schema.json"
    assert schema_path.exists()


@pytest.mark.asyncio
async def test_regenerate_schema_falls_back_to_saved_schema_columns_when_table_unavailable(
    monkeypatch, tmp_path
):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    schema_file = tmp_path / "saved_schema.json"
    schema_file.write_text(
        """
{
  "table_name": "ball_by_ball_ipl",
  "context": "Cricket dataset",
  "columns": [
    {"name": "Batter", "dtype": "VARCHAR", "description": "", "samples": ["V Kohli"]},
    {"name": "Batter Runs", "dtype": "INTEGER", "description": "", "samples": [4]}
  ]
}
""".strip(),
        encoding="utf-8",
    )

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=str(schema_file))

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            allow_schema_sample_values=False,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str):
            self.api_key = api_key
            self.model = model

        def ask(self, _prompt, _schema_type, max_tokens=None):
            return SimpleNamespace(
                schemas=[
                    SimpleNamespace(name="Batter", description="Batter name"),
                    SimpleNamespace(name="Batter Runs", description="Runs scored by batter"),
                ]
            )

    async def _commit():
        return None

    session = SimpleNamespace(commit=_commit)

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(
        runtime_api.DatasetRepository,
        "get_for_workspace_table",
        fake_get_dataset,
    )
    monkeypatch.setattr(
        runtime_api.PreferencesRepository,
        "get_or_create",
        fake_get_prefs,
    )
    monkeypatch.setattr(
        runtime_api.SecretStorageService,
        "get_api_key",
        lambda _user_id: "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("table missing")),
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    result = await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="ball_by_ball_ipl",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Cricket context",
            model="google/gemini-2.5-flash",
        ),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.table_name == "ball_by_ball_ipl"
    assert len(result.columns) == 2
    assert result.columns[0]["description"] == "Batter name"
    assert result.columns[1]["description"] == "Runs scored by batter"
