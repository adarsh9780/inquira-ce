from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_uses_remote_agent_client(monkeypatch):
    captured_payload: dict[str, object] = {}

    async def _fake_preflight(**_kwargs):
        return (
            SimpleNamespace(title="New Conversation"),
            "conv-1",
            {"table_name": "orders", "columns": []},
            "orders",
            "/tmp/ws.db",
        )

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )

    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self
        captured_payload.update(payload)
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "done",
            "output_contract": [],
            "messages": [],
        }

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)

    user = SimpleNamespace(id="user-1", username="alice")
    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=None,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id=None,
        question="show profitability trend",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
    )

    assert payload["is_safe"] is True
    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"
    assert captured_payload["workspace_id"] == "ws-1"
    assert captured_payload["conversation_id"] == "conv-1"
    assert captured_payload["table_name"] == "orders"
    assert captured_payload["agent_profile"] == "agent_v2"
    assert captured_payload["llm"]["api_key"] == "key"
