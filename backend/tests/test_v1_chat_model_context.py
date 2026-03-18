from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_passes_model_and_context_to_graph(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-1", title=title)

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-1")

    async def fake_get_graph(_workspace_id, _memory_path):
        class _Graph:
            async def ainvoke(self, input_state, config=None):
                captured["context"] = input_state.context
                captured["model"] = config.get("configurable", {}).get("model")
                return {"metadata": {"is_safe": True, "is_relevant": True}, "plan": "ok", "current_code": ""}

        return _Graph()

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    langgraph_manager = SimpleNamespace(get_graph=fake_get_graph)
    user = SimpleNamespace(id="u1", username="alice")

    await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=langgraph_manager,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="hello",
        current_code="",
        model="gemini-2.5-pro",
        context="retail demand planning",
        api_key="x",
    )

    assert captured["model"] == "gemini-2.5-pro"
    assert captured["context"] == "retail demand planning"

@pytest.mark.asyncio
async def test_resolve_llm_preferences_includes_selected_coding_model(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="openai/gpt-4.1-mini",
    )

    async def fake_get_or_create(_session, _user_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.services.chat_service.PreferencesRepository.get_or_create",
        fake_get_or_create,
    )

    resolved = await ChatService._resolve_llm_preferences(SimpleNamespace(), "u1")
    assert resolved["selected_coding_model"] == "openai/gpt-4.1-mini"
