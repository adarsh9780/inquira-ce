from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.services.chat_service import ChatService


def _patch_remote_agent(monkeypatch, captured: dict, response: dict | None = None) -> None:
    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self
        captured["payload"] = payload
        return response or {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "ok",
            "messages": [],
        }

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)


@pytest.fixture(autouse=True)
def _stub_llm_preferences(monkeypatch):
    async def _fake_resolve_llm_preferences(_session, _user_id):
        return {
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "requires_api_key": True,
            "selected_lite_model": "google/gemini-2.5-flash-lite",
            "selected_main_model": "google/gemini-2.5-flash",
            "selected_coding_model": "google/gemini-2.5-flash",
            "temperature": 0.0,
            "max_tokens": 2048,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

    monkeypatch.setattr(
        "app.v1.services.chat_service.ChatService._resolve_llm_preferences",
        staticmethod(_fake_resolve_llm_preferences),
    )


@pytest.mark.asyncio
async def test_chat_uses_empty_schema_when_workspace_has_no_dataset(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-1", title=title)

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(id="conv-1", workspace_id="ws-1", title="New Conversation")

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-1")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)

    session = SimpleNamespace(commit=lambda: None)

    async def _commit():
        return None

    session.commit = _commit

    async def _execute(*_args, **_kwargs):
        class _Result:
            def scalar_one_or_none(self):
                return None
        return _Result()

    session.execute = _execute

    user = SimpleNamespace(id="u1", username="alice")

    response, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        api_key="x",
    )

    assert captured["payload"]["table_names"] == []
    assert "active_schema" not in captured["payload"]
    assert response["is_safe"] is True
    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"


@pytest.mark.asyncio
async def test_chat_keeps_backend_columns_when_client_schema_override_present(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-2", title=title)

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(id="conv-2", workspace_id="ws-1", title="New Conversation")

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        return SimpleNamespace(
            table_name="deliveries",
            source_path="browser://deliveries",
            schema_path="/tmp/deliveries_schema.json",
        )

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-2")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return [
            SimpleNamespace(
                table_name="deliveries",
                source_path="browser://deliveries",
                schema_path="/tmp/deliveries_schema.json",
            )
        ]

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    async def fake_load_schema(_path):
        return {"table_name": "deliveries", "columns": []}

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", fake_get_for_workspace_table)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_schema", fake_load_schema)
    async def fake_live_columns(_duckdb_path, _table_name):
        return [{"name": "batter", "dtype": "VARCHAR"}]

    monkeypatch.setattr("app.v1.services.chat_service.ChatService._read_live_table_columns", fake_live_columns)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    async def _execute(*_args, **_kwargs):
        class _Result:
            def scalar_one_or_none(self):
                return None
        return _Result()

    session.execute = _execute

    user = SimpleNamespace(id="u1", username="alice")

    override_schema = {
        "table_name": "deliveries",
        "context": "from-client-context",
        "columns": [{"name": "not_a_real_column", "dtype": "VARCHAR"}],
    }

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="top 10 batsman",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        table_name_override="deliveries",
        active_schema_override=override_schema,
        api_key="x",
    )

    payload = captured["payload"]
    assert payload["table_names"] == ["deliveries"]
    assert "active_schema" not in payload
    assert payload["data_path"] == "/tmp/ws.duckdb"


@pytest.mark.asyncio
async def test_chat_fails_when_explicit_table_override_is_missing(monkeypatch):
    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-missing", title=title)

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        return None

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", fake_get_for_workspace_table)

    session = SimpleNamespace()
    session.commit = lambda: None
    langgraph_manager = SimpleNamespace(get_graph=lambda *_args, **_kwargs: None)
    user = SimpleNamespace(id="u1", username="alice")

    with pytest.raises(HTTPException) as exc:
        await ChatService.analyze_and_persist_turn(
            session=session,
            langgraph_manager=langgraph_manager,
            user=user,
            workspace_id="ws-1",
            conversation_id=None,
            question="hello",
            current_code="",
            model="gemini-2.5-flash",
            context=None,
            table_name_override="missing_table",
            active_schema_override=None,
            api_key="x",
        )

    assert exc.value.status_code == 404
    assert "selected table was not found" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_chat_loads_workspace_schema_for_multiple_tables(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-3", title=title)

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-3")

    async def fake_load_schema(path):
        if path.endswith("orders.json"):
            return {"table_name": "orders", "columns": [{"name": "customer_id", "dtype": "VARCHAR"}]}
        return {"table_name": "customers", "columns": [{"name": "customer_id", "dtype": "VARCHAR"}]}

    async def fake_live_columns(_duckdb_path, table_name):
        if table_name == "orders":
            return [{"name": "order_total", "dtype": "DOUBLE"}]
        return [{"name": "customer_name", "dtype": "VARCHAR"}]

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return [
            SimpleNamespace(table_name="orders", schema_path="/tmp/orders.json"),
            SimpleNamespace(table_name="customers", schema_path="/tmp/customers.json"),
        ]

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_schema", fake_load_schema)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._read_live_table_columns", fake_live_columns)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    user = SimpleNamespace(id="u1", username="alice")

    await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="Which customers have the highest order totals?",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
        api_key="x",
    )

    payload = captured["payload"]
    assert set(payload["table_names"]) == {"orders", "customers"}
    assert "active_schema" not in payload


@pytest.mark.asyncio
async def test_chat_falls_back_to_live_columns_when_schema_file_missing(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-2b", title=title)

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        return SimpleNamespace(
            table_name="deliveries",
            source_path="/tmp/deliveries.csv",
            schema_path="/tmp/missing_schema.json",
        )

    async def fake_load_schema(_path):
        raise HTTPException(status_code=404, detail="missing")

    async def fake_live_columns(_duckdb_path, _table_name):
        return [{"name": "Batter Runs", "dtype": "INTEGER"}]

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-2b")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", fake_get_for_workspace_table)
    async def fake_list_for_workspace(_session, _workspace_id):
        return [
            SimpleNamespace(
                table_name="deliveries",
                source_path="/tmp/deliveries.csv",
                schema_path="/tmp/missing_schema.json",
            )
        ]

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_schema", fake_load_schema)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._read_live_table_columns", fake_live_columns)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    session.execute = lambda *_args, **_kwargs: None

    user = SimpleNamespace(id="u1", username="alice")

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="top runs",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        table_name_override="deliveries",
        active_schema_override=None,
        api_key="x",
    )

    assert captured["payload"]["table_names"] == ["deliveries"]
    assert "active_schema" not in captured["payload"]


@pytest.mark.asyncio
async def test_chat_uses_keychain_api_key_when_payload_key_missing(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-3", title=title)

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-3")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._read_live_table_columns", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key-from-keychain",
    )

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    async def _execute(*_args, **_kwargs):
        class _Result:
            def scalar_one_or_none(self):
                return None
        return _Result()

    session.execute = _execute

    user = SimpleNamespace(id="u1", username="alice")

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        api_key=None,
    )

    assert captured["payload"]["llm"]["api_key"] == "key-from-keychain"


@pytest.mark.asyncio
async def test_chat_allows_ollama_without_api_key(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-ollama", title=title)

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-ollama")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)
    async def _fake_resolve_llm_preferences(_session, _user_id):
        return {
            "provider": "ollama",
            "base_url": "http://localhost:11434/v1",
            "requires_api_key": False,
            "selected_lite_model": "llama3.2:3b",
            "selected_main_model": "llama3.2",
            "selected_coding_model": "llama3.2",
            "temperature": 0.0,
            "max_tokens": 2048,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

    monkeypatch.setattr(
        "app.v1.services.chat_service.ChatService._resolve_llm_preferences",
        staticmethod(_fake_resolve_llm_preferences),
    )
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": None,
    )

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    session.execute = lambda *_args, **_kwargs: None
    user = SimpleNamespace(id="u1", username="alice")

    response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="llama3.2",
        context=None,
        api_key=None,
    )

    assert response["is_safe"] is True
    assert captured["payload"]["llm"]["provider"] == "ollama"
    assert captured["payload"]["llm"]["api_key"] == ""


@pytest.mark.asyncio
async def test_chat_merges_saved_schema_with_live_duckdb_columns(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-4", title=title)

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(id="conv-4", workspace_id="ws-1", title="New Conversation")

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        return SimpleNamespace(
            table_name="ball_by_ball_ipl__5c3afffa",
            source_path="/tmp/ball_by_ball_ipl.csv",
            schema_path="/tmp/ball_by_ball_schema.json",
        )

    async def fake_load_schema(_path):
        return {
            "table_name": "ball_by_ball_ipl__5c3afffa",
            "context": "ipl",
            "columns": [
                {
                    "name": "Batter Runs",
                    "dtype": "INTEGER",
                    "description": "runs scored by batter",
                    "samples": [],
                }
            ],
        }

    async def fake_live_columns(_duckdb_path, _table_name):
        return [
            {"name": "Batter", "dtype": "VARCHAR"},
            {"name": "Batter Runs", "dtype": "INTEGER"},
            {"name": "Runs From Ball", "dtype": "INTEGER"},
        ]

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-4")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", fake_get_for_workspace_table)
    async def fake_list_for_workspace(_session, _workspace_id):
        return [
            SimpleNamespace(
                table_name="ball_by_ball_ipl__5c3afffa",
                source_path="/tmp/ball_by_ball_ipl.csv",
                schema_path="/tmp/ball_by_ball_schema.json",
            )
        ]

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_schema", fake_load_schema)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._read_live_table_columns", fake_live_columns)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    _patch_remote_agent(monkeypatch, captured)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    session.execute = lambda *_args, **_kwargs: None

    user = SimpleNamespace(id="u1", username="alice")

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="top 10 batter by runs",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        table_name_override="ball_by_ball_ipl__5c3afffa",
        active_schema_override=None,
        api_key="x",
    )

    assert captured["payload"]["table_names"] == ["ball_by_ball_ipl__5c3afffa"]
    assert "active_schema" not in captured["payload"]
