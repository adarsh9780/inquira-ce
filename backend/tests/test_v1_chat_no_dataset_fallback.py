from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_uses_empty_schema_when_workspace_has_no_dataset(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1")

    async def fake_create_conversation(*, session, user_id, workspace_id, title):
        return SimpleNamespace(id="conv-1", title=title)

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(id="conv-1", workspace_id="ws-1", title="New Conversation")

    async def fake_get_latest_dataset(_session, _workspace_id):
        return None

    async def fake_get_graph(_workspace_id, _memory_path):
        class _Graph:
            async def ainvoke(self, input_state, config=None):
                captured["schema"] = input_state.active_schema
                return {"metadata": {"is_safe": True, "is_relevant": True}, "plan": "ok", "current_code": ""}

        return _Graph()

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-1")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_latest_for_workspace", fake_get_latest_dataset)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)

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

    langgraph_manager = SimpleNamespace(get_graph=fake_get_graph)
    user = SimpleNamespace(id="u1", username="alice")

    response, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=langgraph_manager,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        api_key="x",
    )

    assert captured["schema"] == {"table_name": "", "columns": []}
    assert response["is_safe"] is True
    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"


@pytest.mark.asyncio
async def test_chat_prefers_client_table_schema_override(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1")

    async def fake_create_conversation(*, session, user_id, workspace_id, title):
        return SimpleNamespace(id="conv-2", title=title)

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(id="conv-2", workspace_id="ws-1", title="New Conversation")

    async def fake_get_latest_dataset(_session, _workspace_id):
        return None

    async def fake_get_for_workspace_table(*, session, workspace_id, table_name):
        return SimpleNamespace(
            table_name="deliveries",
            source_path="browser://deliveries",
            schema_path="/tmp/deliveries_schema.json",
        )

    async def fake_get_graph(_workspace_id, _memory_path):
        class _Graph:
            async def ainvoke(self, input_state, config=None):
                captured["schema"] = input_state.active_schema
                captured["table_name"] = input_state.table_name
                return {"metadata": {"is_safe": True, "is_relevant": True}, "plan": "ok", "current_code": ""}

        return _Graph()

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-2")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_latest_for_workspace", fake_get_latest_dataset)
    async def fake_load_schema(_path):
        return {"table_name": "deliveries", "columns": []}

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", fake_get_for_workspace_table)
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_schema", fake_load_schema)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)

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

    langgraph_manager = SimpleNamespace(get_graph=fake_get_graph)
    user = SimpleNamespace(id="u1", username="alice")

    override_schema = {
        "table_name": "deliveries",
        "columns": [{"name": "batter", "dtype": "VARCHAR"}],
    }

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=langgraph_manager,
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

    assert captured["table_name"] == "deliveries"
    assert captured["schema"]["table_name"] == "deliveries"
    assert captured["schema"]["columns"][0]["name"] == "batter"


@pytest.mark.asyncio
async def test_chat_uses_keychain_api_key_when_payload_key_missing(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1")

    async def fake_create_conversation(*, session, user_id, workspace_id, title):
        return SimpleNamespace(id="conv-3", title=title)

    async def fake_get_latest_dataset(_session, _workspace_id):
        return None

    async def fake_get_graph(_workspace_id, _memory_path):
        class _Graph:
            async def ainvoke(self, input_state, config=None):
                captured["api_key"] = config["configurable"].get("api_key")
                return {"metadata": {"is_safe": True, "is_relevant": True}, "plan": "ok", "current_code": ""}

        return _Graph()

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-3")

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_latest_for_workspace", fake_get_latest_dataset)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    monkeypatch.setattr("app.v1.services.chat_service.SecretStorageService.get_api_key", lambda _uid: "key-from-keychain")

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

    langgraph_manager = SimpleNamespace(get_graph=fake_get_graph)
    user = SimpleNamespace(id="u1", username="alice")

    _response, _conversation_id, _turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=langgraph_manager,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="gemini-2.5-flash",
        context=None,
        api_key=None,
    )

    assert captured["api_key"] == "key-from-keychain"

