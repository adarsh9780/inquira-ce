from app.agent_v2.tools.sample_data import sample_data


def test_sample_data_returns_error_payload_when_duckdb_connect_fails(monkeypatch):
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    def fail_connect(*_args, **_kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr("app.agent_v2.tools.sample_data.emit_agent_event", fake_emit)
    monkeypatch.setattr("app.agent_v2.tools.sample_data.duckdb.connect", fail_connect)

    result = sample_data(data_path="/tmp/ws.duckdb", table_name="deliveries", limit=5)

    assert result["rows"] == []
    assert result["columns"] == []
    assert result["row_count"] == 0
    assert "locked" in str(result.get("error") or "")
    assert any(event == "tool_call" for event, _payload in events)
    assert any(
        event == "tool_result" and payload.get("status") == "error"
        for event, payload in events
    )
