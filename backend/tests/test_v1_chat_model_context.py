from types import SimpleNamespace

import pytest

from app.agent.graph import InquiraAgent
from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_passes_model_and_context_to_graph(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1")

    async def fake_create_conversation(*, session, user_id, workspace_id, title):
        return SimpleNamespace(id="conv-1", title=title)

    async def fake_get_latest_dataset(_session, _workspace_id):
        return None

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
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_latest_for_workspace", fake_get_latest_dataset)
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


def test_agent_model_selection_uses_configurable_model(monkeypatch):
    called = {}

    def fake_init_chat_model(model_ref):
        called["model_ref"] = model_ref
        return object()

    monkeypatch.setattr("app.agent.graph.init_chat_model", fake_init_chat_model)

    agent = InquiraAgent()
    agent._get_model(
        {"configurable": {"model": "gemini-2.5-pro", "api_key": "key"}},
        model_name="gemini-2.5-flash",
    )

    assert called["model_ref"] == "google_genai:gemini-2.5-pro"
