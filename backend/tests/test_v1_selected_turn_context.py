from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_builds_selected_turn_context_when_flag_enabled(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/ws.duckdb")

    async def fake_get_conversation(_session, _conversation_id):
        return SimpleNamespace(
            id="conv-1",
            workspace_id="ws-1",
            title="Conversation",
            branch_summary_json='[{"turn_id":"turn-0","question":"baseline"}]',
            schema_memory_json='{"tables_loaded":["orders"]}',
        )

    async def fake_get_turn(_session, _turn_id):
        return SimpleNamespace(
            id="turn-1",
            conversation_id="conv-1",
            user_text="Earlier question",
            assistant_text="Earlier answer",
            code_snapshot="print('older code')",
        )

    async def fake_next_seq_no(_session, _conversation_id):
        return 2

    async def fake_create_turn(*, session, **kwargs):
        _ = session, kwargs
        return SimpleNamespace(id="turn-2")

    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self
        captured["context"] = payload.get("context")
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "ok",
            "messages": [],
        }

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_conversation", fake_get_conversation)
    async def fake_list_for_workspace(_session, _workspace_id):
        return []

    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.chat_service.DatasetRepository.get_for_workspace_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.get_turn", fake_get_turn)
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
            "context_windows": {},
        }
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._resolve_llm_preferences", staticmethod(_fake_resolve_llm_preferences))
    async def _fake_load_workspace_schema(**kwargs):
        _ = kwargs
        return {"table_name": "", "tables": []}
    monkeypatch.setattr("app.v1.services.chat_service.ChatService._load_workspace_schema", staticmethod(_fake_load_workspace_schema))

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
        conversation_id="conv-1",
        question="New question",
        current_code="",
        model="gemini-2.5-flash",
        context="top-level context",
        use_selected_turn_context=True,
        selected_parent_turn_id="turn-1",
        api_key="x",
    )

    context = str(captured["context"])
    assert "Selected parent turn context:" in context
    assert "Earlier question" in context
    assert "print('older code')" in context
    assert "Branch summary JSON:" in context
    assert "Conversation schema memory JSON:" in context
