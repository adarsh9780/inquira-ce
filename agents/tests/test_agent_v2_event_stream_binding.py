from agent_v2.events import emit_agent_event
from agent_v2.graph import _with_stream_event_emitter


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
