from agent_v2.events import emit_agent_event
from agent_v2.graph import _with_stream_event_emitter
from agent_v2.nodes import route_node
from agent_v2.router import RouteDecision

import pytest


def test_agent_v2_stream_event_binding_emits_custom_payload(monkeypatch):
    captured: list[dict] = []

    def _writer(payload):
        captured.append(payload)

    monkeypatch.setattr("langgraph.config.get_stream_writer", lambda: _writer)

    def _node(_state, _config):
        emit_agent_event("agent_status", {"message": "searching schema"})
        return {"ok": True}

    wrapped = _with_stream_event_emitter(_node)
    result = wrapped({}, {})

    assert result == {"ok": True}
    assert captured == [{"event": "agent_status", "data": {"message": "searching schema"}}]

    # Emitter is request-scoped and should not leak outside the wrapped node call.
    emit_agent_event("tool_call", {"call_id": "outside"})
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_route_node_emits_user_facing_reasoning(monkeypatch):
    captured: list[tuple[str, dict]] = []

    async def _fake_decide_route_details(_messages, _configurable):
        return RouteDecision(
            route="analysis",
            reasoning="I understand you want compare batting metrics, so I need inspect data context before answering.",
        )

    monkeypatch.setattr("agent_v2.nodes.decide_route_details", _fake_decide_route_details)
    monkeypatch.setattr("agent_v2.nodes.emit_agent_event", lambda event, payload: captured.append((event, payload)))

    result = await route_node({"messages": []}, {"configurable": {}})

    assert result["route"] == "analysis"
    assert result["metadata"] == {"is_safe": True, "is_relevant": True}
    assert captured == [
        (
            "reasoning",
            {
                "stage": "intent",
                "message": "I understand you want compare batting metrics, so I need inspect data context before answering.",
                "route": "analysis",
            },
        )
    ]
