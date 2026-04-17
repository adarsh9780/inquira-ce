from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api import runtime as runtime_api


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
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.2,
            llm_max_tokens=512,
            llm_top_p=0.95,
            llm_top_k=0,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    class FakeLLMService:
        def __init__(
            self,
            api_key: str,
            model: str,
            provider: str | None = None,
            temperature: float = 0.0,
            max_tokens: int | None = None,
            top_p: float | None = None,
            top_k: int | None = None,
            frequency_penalty: float | None = None,
            presence_penalty: float | None = None,
        ):
            captured["api_key"] = api_key
            captured["model"] = model
            captured["temperature"] = temperature
            captured["init_max_tokens"] = max_tokens
            captured["top_p"] = top_p
            captured["top_k"] = top_k
            captured["frequency_penalty"] = frequency_penalty
            captured["presence_penalty"] = presence_penalty

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
        lambda _user_id, provider="openrouter": "test-key",
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
    assert captured["temperature"] == 0.2
    assert captured["init_max_tokens"] == 512
    assert captured["top_p"] == 0.95
    assert captured["top_k"] == 0
    assert captured["max_tokens"] == 512
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
        lambda _user_id, provider="openrouter": "test-key",
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


@pytest.mark.asyncio
async def test_regenerate_schema_matches_descriptions_with_normalized_names(monkeypatch, tmp_path):
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
            _ = (api_key, model)

        def ask(self, _prompt, _schema_type, max_tokens=None):
            _ = max_tokens
            return SimpleNamespace(
                schemas=[
                    SimpleNamespace(name="order id", description="Unique order identifier"),
                    SimpleNamespace(name="CUSTOMERNAME", description="Customer full name"),
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
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "Order_ID", "dtype": "INTEGER", "samples": [], "description": ""},
            {"name": "customer_name", "dtype": "VARCHAR", "samples": [], "description": ""},
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
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.table_name == "orders"
    assert result.columns[0]["name"] == "Order_ID"
    assert result.columns[0]["description"] == "Unique order identifier"
    assert result.columns[1]["name"] == "customer_name"
    assert result.columns[1]["description"] == "Customer full name"


@pytest.mark.asyncio
async def test_regenerate_schema_requires_all_advanced_llm_preferences(monkeypatch, tmp_path):
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
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.2,
            llm_max_tokens=512,
            llm_top_p=0.95,
            llm_top_k=None,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    class FakeLLMService:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)
            raise AssertionError("LLMService should not initialize when settings are missing")

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
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "amount", "dtype": "INTEGER", "samples": [], "description": ""}
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

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

    assert exc_info.value.status_code == 400
    assert "llm_top_k" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_regenerate_schema_uses_lite_model_by_default(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    captured: dict[str, str] = {}

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=None)

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.2,
            llm_max_tokens=512,
            llm_top_p=0.95,
            llm_top_k=0,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None, **_kwargs):
            _ = (api_key, provider)
            captured["model"] = model

        def ask(self, _prompt, _schema_type, max_tokens=None):
            _ = max_tokens
            return SimpleNamespace(
                schemas=[SimpleNamespace(name="amount", description="Amount column", aliases=[])]
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
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "amount", "dtype": "INTEGER", "samples": [], "description": ""}
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="amounts",
        payload=runtime_api.RegenerateSchemaRequest(context="Test context"),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert captured["model"] == "google/gemini-2.5-flash-lite"


@pytest.mark.asyncio
async def test_regenerate_schema_splits_on_length_limit_until_single_column(monkeypatch, tmp_path):
    duckdb_path = tmp_path / "workspace.duckdb"
    duckdb_path.touch()
    batch_sizes: list[int] = []

    async def fake_require_workspace_access(_session, _user_id, _workspace_id):
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    async def fake_get_dataset(*, session, workspace_id, table_name):
        return SimpleNamespace(schema_path=None)

    async def fake_get_prefs(_session, _user_id):
        return SimpleNamespace(
            schema_context="Default context",
            selected_model="google/gemini-2.5-flash",
            selected_lite_model="google/gemini-2.5-flash-lite",
            allow_schema_sample_values=False,
            llm_temperature=0.2,
            llm_max_tokens=1024,
            llm_top_p=0.95,
            llm_top_k=0,
            llm_frequency_penalty=0.0,
            llm_presence_penalty=0.0,
        )

    def _columns_from_prompt(prompt: str) -> list[str]:
        after_columns = prompt.split("Columns:\n", 1)[1]
        section = after_columns.split("\n\nFor every column", 1)[0]
        names: list[str] = []
        for line in section.splitlines():
            line = line.strip()
            if not line.startswith("- "):
                continue
            names.append(line[2:].split(" (", 1)[0].strip())
        return names

    class FakeLLMService:
        def __init__(self, api_key: str, model: str, provider: str | None = None, **_kwargs):
            _ = (api_key, model, provider)

        def ask(self, prompt, _schema_type, max_tokens=None):
            _ = max_tokens
            names = _columns_from_prompt(prompt)
            batch_sizes.append(len(names))
            if len(names) > 1:
                raise HTTPException(
                    status_code=500,
                    detail="Could not parse response content as the length limit was reached",
                )
            name = names[0]
            return SimpleNamespace(
                schemas=[
                    SimpleNamespace(
                        name=name,
                        description=f"{name} description",
                        aliases=[f"{name} alias"],
                    )
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
        lambda _user_id, provider="openrouter": "test-key",
    )
    monkeypatch.setattr(
        runtime_api,
        "_read_table_columns_for_prompt",
        lambda *_args, **_kwargs: [
            {"name": "col_a", "dtype": "INTEGER", "samples": [], "description": ""},
            {"name": "col_b", "dtype": "INTEGER", "samples": [], "description": ""},
            {"name": "col_c", "dtype": "INTEGER", "samples": [], "description": ""},
            {"name": "col_d", "dtype": "INTEGER", "samples": [], "description": ""},
        ],
    )
    monkeypatch.setattr(runtime_api, "LLMService", FakeLLMService)

    result = await runtime_api.regenerate_workspace_dataset_schema(
        workspace_id="ws-1",
        table_name="amounts",
        payload=runtime_api.RegenerateSchemaRequest(context="Test context"),
        session=session,
        current_user=SimpleNamespace(id="user-1"),
    )

    assert result.table_name == "amounts"
    assert [column["description"] for column in result.columns] == [
        "col_a description",
        "col_b description",
        "col_c description",
        "col_d description",
    ]
    assert batch_sizes.count(4) == 1
    assert batch_sizes.count(2) == 2
    assert batch_sizes.count(1) == 4
