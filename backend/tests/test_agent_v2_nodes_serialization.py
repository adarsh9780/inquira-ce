from datetime import datetime
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from app.agent_v2.nodes import AnalysisOutput, react_loop_node


class _FakePrompt:
    def __or__(self, _rhs):
        return object()


class _FakeModel:
    def with_structured_output(self, _schema):
        return object()


@pytest.mark.asyncio
async def test_react_loop_node_serializes_non_json_sample_values(monkeypatch):
    captured_payload: dict[str, str] = {}

    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=1, turn_timeout=120),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.inspect_schema",
        lambda **_kwargs: {
            "table_name": "deliveries",
            "columns": [{"name": "ts", "dtype": "TIMESTAMP"}],
        },
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.sample_data",
        lambda **_kwargs: {
            "rows": [{"ts": datetime(2026, 1, 2, 3, 4, 5)}],
            "columns": ["ts"],
            "row_count": 1,
        },
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.ChatPromptTemplate.from_messages",
        lambda *_args, **_kwargs: _FakePrompt(),
    )
    monkeypatch.setattr("app.agent_v2.nodes._get_model", lambda *_args, **_kwargs: _FakeModel())
    monkeypatch.setattr(
        "app.agent_v2.nodes.guard_code",
        lambda code, table_name=None: SimpleNamespace(blocked=False, code=code, reason=None),
    )

    async def fake_execute_python(**_kwargs):
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)
    monkeypatch.setattr("app.agent_v2.nodes.emit_stream_token", lambda *_args, **_kwargs: None)

    def fake_invoke(_chain, payload):
        captured_payload.update(payload)
        return AnalysisOutput(
            code="print('ok')",
            explanation="done",
            output_contract=[],
        )

    monkeypatch.setattr("app.agent_v2.nodes._invoke_structured_chain", fake_invoke)

    result = await react_loop_node(
        {
            "messages": [HumanMessage(content="show sample")],
            "table_name": "deliveries",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "deliveries", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
        },
        {"configurable": {"api_key": "key"}},
    )

    assert result["final_code"] == "print('ok')"
    assert captured_payload.get("workspace_db_path") == "/tmp/ws.duckdb"
    assert "2026-01-02" in str(captured_payload.get("sample_json") or "")
