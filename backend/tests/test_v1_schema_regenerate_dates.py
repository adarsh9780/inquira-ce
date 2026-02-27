import pytest
from types import SimpleNamespace
import json
from datetime import date, datetime
from pathlib import Path

from app.v1.api import runtime as runtime_api

@pytest.mark.asyncio
async def test_regenerate_schema_handles_date_types(monkeypatch, tmp_path):
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
            allow_schema_sample_values=True,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str):
            pass

        def ask(self, _prompt, _schema_type, max_tokens=None):
            return SimpleNamespace(
                schemas=[SimpleNamespace(name="date_col", description="Date column")]
            )

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
    
    # Simulate an extracted column sample from DuckDB that contains a native date object
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {
                "name": "date_col", 
                "dtype": "DATE", 
                "samples": [date(2023, 1, 1), datetime(2023, 1, 1, 12, 0, 0)], 
                "description": ""
            }
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    async def fake_commit():
        return None
    session = SimpleNamespace(commit=fake_commit)

    # This should not raise a TypeError (Object of type date is not JSON serializable)
    await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="dates",
        payload=runtime_api.RegenerateSchemaRequest(
            context="Test context",
            model="google/gemini-2.5-flash",
        ),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )
    
    schema_path = Path(duckdb_path).parent / "meta" / "dates_schema.json"
    assert schema_path.exists()
    
    with schema_path.open() as f:
        data = json.load(f)
        
    assert data["columns"][0]["samples"][0] == "2023-01-01"
    assert data["columns"][0]["samples"][1] == "2023-01-01T12:00:00"
