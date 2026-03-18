from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


class _FakeGraph:
    async def astream(self, _input_state, config=None):
        from app.agent_v2.streaming import emit_stream_token

        emit_stream_token("create_plan", "Hello")
        emit_stream_token("create_plan", " world")
        yield {"create_plan": {"plan": "Hello world"}}

    async def aget_state(self, config=None):
        return SimpleNamespace(
            values={
                "metadata": {"is_safe": True, "is_relevant": True},
                "plan": "Hello world",
                "current_code": "",
                "messages": [],
            }
        )


class _FakeLanggraphManager:
    async def get_graph(self, _workspace_id, _memory_path):
        return _FakeGraph()


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

    user = SimpleNamespace(id="user-1", username="alice")
    events = []
    async for event in ChatService.analyze_and_stream_turns(
        session=None,
        langgraph_manager=_FakeLanggraphManager(),
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
