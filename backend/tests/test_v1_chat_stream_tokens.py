from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_v1_chat_stream_emits_token_events_before_final(monkeypatch):
    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-1", {}, "tbl", "/tmp/ws.db")

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr(
        "app.v1.services.chat_service.SecretStorageService.get_api_key",
        lambda _uid, provider="openrouter": "key",
    )
    monkeypatch.setattr(
        "app.v1.services.chat_service.AgentClient.assert_health",
        lambda _self: _fake_health(),
    )
    monkeypatch.setattr(
        "app.v1.services.chat_service.AgentClient.stream",
        lambda _self, _payload: _fake_stream(),
    )

    async def _fake_health():
        return {"status": "ok", "api_major": 1}

    async def _fake_stream():
        yield {"event": "token", "data": {"node": "create_plan", "text": "Hello"}}
        yield {"event": "token", "data": {"node": "create_plan", "text": " world"}}
        yield {"event": "node", "data": {"node": "create_plan", "output": "Hello world"}}
        yield {
            "event": "final",
            "data": {
                "run_id": "run-1",
                "result": {
                    "metadata": {"is_safe": True, "is_relevant": True},
                    "plan": "Hello world",
                    "current_code": "",
                    "messages": [],
                },
            },
        }

    user = SimpleNamespace(id="user-1", username="alice")
    events = []
    async for event in ChatService.analyze_and_stream_turns(
        session=None,
        langgraph_manager=None,
        user=user,
        workspace_id="ws-1",
        conversation_id="conv-1",
        question="hello",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
        table_name_override=None,
        active_schema_override=None,
        api_key=None,
    ):
        events.append(event)

    token_events = [evt for evt in events if evt.get("event") == "token"]
    node_events = [evt for evt in events if evt.get("event") == "node"]
    final_events = [evt for evt in events if evt.get("event") == "final"]

    assert token_events
    assert "".join(evt["data"]["text"] for evt in token_events) == "Hello world"
    assert node_events
    assert node_events[0]["data"]["node"] == "create_plan"
    assert node_events[0]["data"]["output"] == "Hello world"
    assert final_events
    assert events.index(token_events[0]) < events.index(final_events[0])
