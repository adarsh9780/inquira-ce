from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_passes_model_and_context_to_agent_payload(monkeypatch):
    captured = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_create_conversation(*, session, principal_id, workspace_id, title):
        return SimpleNamespace(id="conv-1", title=title)

    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    async def fake_create_turn(*, session, **kwargs):
        return SimpleNamespace(id="turn-1")

    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self
        captured["context"] = payload.get("context")
        captured["model"] = payload.get("model")
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "ok",
            "messages": [],
        }

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationService.create_conversation", fake_create_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)
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
        llm_temperature=0.0,
        llm_max_tokens=2048,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
    )

    async def fake_get_or_create(_session, _user_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.services.chat_service.PreferencesRepository.get_or_create",
        fake_get_or_create,
    )

    resolved = await ChatService._resolve_llm_preferences(SimpleNamespace(), "u1")
    assert resolved["selected_coding_model"] == "openai/gpt-4.1-mini"
    assert resolved["top_k"] == 0


@pytest.mark.asyncio
async def test_resolve_llm_preferences_uses_persisted_ollama_base_url(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="ollama",
        selected_model="gpt-oss:20b-cloud",
        selected_lite_model="llama3.2:3b",
        selected_coding_model="gpt-oss:20b-cloud",
        provider_model_catalogs_json='{"ollama":{"base_url":"http://localhost:11434/api"}}',
        llm_temperature=0.0,
        llm_max_tokens=2048,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
    )

    async def fake_get_or_create(_session, _user_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.services.chat_service.PreferencesRepository.get_or_create",
        fake_get_or_create,
    )

    resolved = await ChatService._resolve_llm_preferences(SimpleNamespace(), "u1")
    assert resolved["provider"] == "ollama"
    assert resolved["base_url"] == "http://localhost:11434/v1"
