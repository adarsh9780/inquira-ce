"""Tests for ephemeral agent_status events emitted during react_loop_node."""

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
async def test_react_loop_emits_agent_status_on_success(monkeypatch):
    """Verify generating_code, executing_code, and execution_success events are emitted."""
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    monkeypatch.setattr("app.agent_v2.nodes.emit_agent_event", fake_emit)
    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=1, turn_timeout=120, max_tool_calls=1),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.sample_data",
        lambda **_kwargs: {"rows": [], "columns": [], "row_count": 0},
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
    monkeypatch.setattr("app.agent_v2.nodes.emit_stream_token", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.agent_v2.nodes._invoke_structured_chain",
        lambda _chain, _payload: AnalysisOutput(
            code="print('ok')", explanation="done", output_contract=[]
        ),
    )

    async def fake_execute_python(**_kwargs):
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    await react_loop_node(
        {
            "messages": [HumanMessage(content="show data")],
            "table_name": "test_table",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "test_table", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
        },
        {"configurable": {"api_key": "key"}},
    )

    status_events = [(e, p) for e, p in events if e == "agent_status"]
    steps = [p["step"] for _, p in status_events]

    assert "generating_code" in steps, f"Expected generating_code step, got: {steps}"
    assert "executing_code" in steps, f"Expected executing_code step, got: {steps}"
    assert "execution_success" in steps, f"Expected execution_success step, got: {steps}"


@pytest.mark.asyncio
async def test_react_loop_emits_agent_status_on_retry(monkeypatch):
    """Verify execution_retry event is emitted when code fails and retries."""
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    monkeypatch.setattr("app.agent_v2.nodes.emit_agent_event", fake_emit)
    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=2, turn_timeout=120, max_tool_calls=1),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.sample_data",
        lambda **_kwargs: {"rows": [], "columns": [], "row_count": 0},
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
    monkeypatch.setattr("app.agent_v2.nodes.emit_stream_token", lambda *_args, **_kwargs: None)

    call_count = 0
    outputs = [
        AnalysisOutput(code="bad_code()", explanation="first try", output_contract=[]),
        AnalysisOutput(code="good_code()", explanation="fixed", output_contract=[]),
    ]

    def fake_invoke(_chain, _payload):
        nonlocal call_count
        result = outputs[min(call_count, len(outputs) - 1)]
        call_count += 1
        return result

    monkeypatch.setattr("app.agent_v2.nodes._invoke_structured_chain", fake_invoke)

    execution_count = 0

    async def fake_execute_python(**_kwargs):
        nonlocal execution_count
        execution_count += 1
        if execution_count == 1:
            return {"success": False, "error": "NameError: bad_code", "stderr": "NameError"}
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    await react_loop_node(
        {
            "messages": [HumanMessage(content="analyze data")],
            "table_name": "test_table",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "test_table", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
        },
        {"configurable": {"api_key": "key"}},
    )

    status_events = [(e, p) for e, p in events if e == "agent_status"]
    steps = [p["step"] for _, p in status_events]

    assert "execution_retry" in steps, f"Expected execution_retry step, got: {steps}"
    # Should mention retry attempt number in message
    retry_events = [p for _, p in status_events if p["step"] == "execution_retry"]
    assert any("Retrying" in p["message"] for p in retry_events)


@pytest.mark.asyncio
async def test_react_loop_emits_agent_status_on_code_guard_failure(monkeypatch):
    """Verify code_validation_failed event is emitted when code guard blocks."""
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    monkeypatch.setattr("app.agent_v2.nodes.emit_agent_event", fake_emit)
    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=2, turn_timeout=120, max_tool_calls=1),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.sample_data",
        lambda **_kwargs: {"rows": [], "columns": [], "row_count": 0},
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.ChatPromptTemplate.from_messages",
        lambda *_args, **_kwargs: _FakePrompt(),
    )
    monkeypatch.setattr("app.agent_v2.nodes._get_model", lambda *_args, **_kwargs: _FakeModel())
    monkeypatch.setattr("app.agent_v2.nodes.emit_stream_token", lambda *_args, **_kwargs: None)

    call_count = 0

    def fake_guard(code, table_name=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return SimpleNamespace(blocked=True, code="", reason="Unsafe import detected")
        return SimpleNamespace(blocked=False, code=code, reason=None)

    monkeypatch.setattr("app.agent_v2.nodes.guard_code", fake_guard)

    outputs = iter([
        AnalysisOutput(code="import os; os.remove('/')", explanation="bad", output_contract=[]),
        AnalysisOutput(code="print('safe')", explanation="good", output_contract=[]),
    ])
    monkeypatch.setattr(
        "app.agent_v2.nodes._invoke_structured_chain",
        lambda _chain, _payload: next(outputs),
    )

    async def fake_execute_python(**_kwargs):
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    await react_loop_node(
        {
            "messages": [HumanMessage(content="do something")],
            "table_name": "test_table",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "test_table", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
        },
        {"configurable": {"api_key": "key"}},
    )

    status_events = [(e, p) for e, p in events if e == "agent_status"]
    steps = [p["step"] for _, p in status_events]

    assert "code_validation_failed" in steps, f"Expected code_validation_failed step, got: {steps}"


@pytest.mark.asyncio
async def test_react_loop_emits_agent_status_on_schema_search(monkeypatch):
    """Verify searching_schema event is emitted when agent searches for column details."""
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    monkeypatch.setattr("app.agent_v2.nodes.emit_agent_event", fake_emit)
    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=1, turn_timeout=120, max_tool_calls=3),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.sample_data",
        lambda **_kwargs: {"rows": [], "columns": [], "row_count": 0},
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
    monkeypatch.setattr("app.agent_v2.nodes.emit_stream_token", lambda *_args, **_kwargs: None)

    outputs = iter([
        AnalysisOutput(
            code="",
            explanation="need schema",
            output_contract=[],
            search_schema_queries=["revenue"],
        ),
        AnalysisOutput(
            code="print('revenue')",
            explanation="found it",
            output_contract=[],
            search_schema_queries=[],
        ),
    ])
    monkeypatch.setattr(
        "app.agent_v2.nodes._invoke_structured_chain",
        lambda _chain, _payload: next(outputs),
    )
    monkeypatch.setattr(
        "app.agent_v2.nodes.search_schema",
        lambda **_kwargs: {
            "query": "revenue",
            "match_count": 1,
            "columns": [{"table_name": "sales", "name": "revenue", "dtype": "DOUBLE", "description": ""}],
        },
    )

    async def fake_execute_python(**_kwargs):
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    await react_loop_node(
        {
            "messages": [HumanMessage(content="show revenue")],
            "table_name": "sales",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "sales", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
            "known_columns": [],
        },
        {"configurable": {"api_key": "key"}},
    )

    status_events = [(e, p) for e, p in events if e == "agent_status"]
    steps = [p["step"] for _, p in status_events]

    assert "searching_schema" in steps, f"Expected searching_schema step, got: {steps}"
    search_events = [p for _, p in status_events if p["step"] == "searching_schema"]
    assert any("revenue" in p["message"].lower() for p in search_events)
