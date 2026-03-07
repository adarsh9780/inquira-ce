import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.api import runtime as runtime_api


def test_schema_description_item_aliases_default_empty_list():
    item = runtime_api.SchemaDescriptionItem(name="gross_margin", description="Profitability metric")
    assert item.aliases == []


@pytest.mark.asyncio
async def test_regenerate_schema_persists_aliases(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=None)

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Retail context",
            selected_model="google/gemini-2.5-flash",
            allow_schema_sample_values=False,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None):
            _ = (api_key, model)

        def ask(self, _prompt, _schema_type, max_tokens=None):
            _ = max_tokens
            return SimpleNamespace(
                schemas=[
                    SimpleNamespace(
                        name="gross_margin",
                        description="Profitability percentage",
                        aliases=["profitability", "margin pct", "gross profit ratio"],
                    )
                ]
            )

    async def _commit():
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api.PreferencesRepository, "get_or_create", fake_get_prefs)
    monkeypatch.setattr(
        runtime_api.SecretStorageService,
        "get_api_key",
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "gross_margin", "dtype": "DOUBLE", "samples": [], "description": "", "aliases": []}
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    result = await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="orders",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Retail context",
            model="google/gemini-2.5-flash",
        ),
        session=SimpleNamespace(commit=_commit),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.columns[0]["aliases"] == ["profitability", "margin pct", "gross profit ratio"]

    schema_path = Path(duckdb_path).parent / "meta" / "orders_schema.json"
    assert schema_path.exists()
    saved = json.loads(schema_path.read_text(encoding="utf-8"))
    assert saved["columns"][0]["aliases"] == ["profitability", "margin pct", "gross profit ratio"]


@pytest.mark.asyncio
async def test_regenerate_schema_missing_aliases_defaults_to_empty(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=None)

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Retail context",
            selected_model="google/gemini-2.5-flash",
            allow_schema_sample_values=False,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None):
            _ = (api_key, model)

        def ask(self, _prompt, _schema_type, max_tokens=None):
            _ = max_tokens
            return SimpleNamespace(
                schemas=[
                    SimpleNamespace(
                        name="gross_margin",
                        description="Profitability percentage",
                    )
                ]
            )

    async def _commit():
        return None

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(runtime_api.DatasetRepository, "get_for_workspace_table", fake_get_dataset)
    monkeypatch.setattr(runtime_api.PreferencesRepository, "get_or_create", fake_get_prefs)
    monkeypatch.setattr(
        runtime_api.SecretStorageService,
        "get_api_key",
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "gross_margin", "dtype": "DOUBLE", "samples": [], "description": ""}
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    result = await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="orders",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Retail context",
            model="google/gemini-2.5-flash",
        ),
        session=SimpleNamespace(commit=_commit),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.columns[0]["aliases"] == []
