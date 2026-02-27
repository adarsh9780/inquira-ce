import pytest
from types import SimpleNamespace
from fastapi import HTTPException
from pathlib import Path

from app.v1.api import runtime as runtime_api

@pytest.mark.asyncio
async def test_regenerate_schema_raises_500_on_llm_failure(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()

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
            pass

        def ask(self, _prompt, _schema_type, max_tokens=None):
            raise RuntimeError("API rate limit exceeded")

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

    session = SimpleNamespace(commit=lambda: None)

    with pytest.raises(HTTPException) as exc_info:
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
    
    assert exc_info.value.status_code == 500
    assert "Failed to generate schema via LLM: API rate limit exceeded" in exc_info.value.detail
