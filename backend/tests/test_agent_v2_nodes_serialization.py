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
        lambda: SimpleNamespace(max_code_executions=1, turn_timeout=120, max_tool_calls=3),
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
    assert str(captured_payload.get("schema_summary") or "") == "No schema columns available."
    assert "2026-01-02" in str(captured_payload.get("sample_json") or "")
    assert captured_payload.get("known_columns_json") == "[]"


@pytest.mark.asyncio
async def test_react_loop_node_retries_after_runtime_error(monkeypatch):
    payloads: list[dict] = []
    executed_codes: list[str] = []
    outputs = iter(
        [
            AnalysisOutput(
                code='years_df = conn.sql("select 1 as year").fetch_df()',
                explanation="initial explanation",
                output_contract=[],
            ),
            AnalysisOutput(
                code='years_df = conn.sql("select 1 as year").fetchdf()',
                explanation="fixed explanation",
                output_contract=[],
            ),
        ]
    )

    monkeypatch.setattr(
        "app.agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(max_code_executions=2, turn_timeout=120, max_tool_calls=3),
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

    def fake_invoke(_chain, payload):
        payloads.append(payload)
        return next(outputs)

    async def fake_execute_python(**kwargs):
        code = str(kwargs.get("code") or "")
        executed_codes.append(code)
        if "fetch_df(" in code:
            return {
                "success": False,
                "error": "AttributeError: This relation does not contain a column by the name of 'fetch_df'",
                "stderr": "AttributeError: This relation does not contain a column by the name of 'fetch_df'",
            }
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes._invoke_structured_chain", fake_invoke)
    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    result = await react_loop_node(
        {
            "messages": [HumanMessage(content="how many years of data we have?")],
            "table_name": "ball_by_ball_ipl__5c3afffa",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {"table_name": "ball_by_ball_ipl__5c3afffa", "columns": []},
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
        },
        {"configurable": {"api_key": "key"}},
    )

    assert len(executed_codes) == 2
    assert "fetch_df(" in executed_codes[0]
    assert "fetchdf(" in executed_codes[1]
    assert result["final_code"] == 'years_df = conn.sql("select 1 as year").fetchdf()'
    assert "Execution warning:" not in result["final_explanation"]
    retry_messages = payloads[1]["messages"]
    assert any(
        "Runtime error: AttributeError" in str(getattr(message, "content", ""))
        for message in retry_messages
    )


@pytest.mark.asyncio
async def test_react_loop_node_merges_search_schema_results_into_known_columns(monkeypatch):
    payloads: list[dict] = []
    outputs = iter(
        [
            AnalysisOutput(
                code="",
                explanation="Need schema details first",
                output_contract=[],
                search_schema_queries=["profitability"],
            ),
            AnalysisOutput(
                code='result_df = conn.sql("select gross_margin from orders").fetchdf()',
                explanation="Computed profitability output",
                output_contract=[],
                search_schema_queries=[],
            ),
        ]
    )

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

    def fake_invoke(_chain, payload):
        payloads.append(payload)
        return next(outputs)

    monkeypatch.setattr("app.agent_v2.nodes._invoke_structured_chain", fake_invoke)
    monkeypatch.setattr(
        "app.agent_v2.nodes.search_schema",
        lambda **_kwargs: {
            "query": "profitability",
            "match_count": 1,
            "columns": [
                {
                    "table_name": "orders",
                    "name": "gross_margin",
                    "dtype": "DOUBLE",
                    "description": "Profitability percentage",
                }
            ],
        },
    )

    async def fake_execute_python(**_kwargs):
        return {"success": True}

    monkeypatch.setattr("app.agent_v2.nodes.execute_python", fake_execute_python)

    result = await react_loop_node(
        {
            "messages": [HumanMessage(content="show profitability trend")],
            "table_name": "orders",
            "data_path": "/tmp/ws.duckdb",
            "active_schema": {
                "table_name": "orders",
                "columns": [
                    {"name": "gross_margin", "dtype": "DOUBLE", "description": "", "aliases": ["profitability"]}
                ],
            },
            "workspace_id": "ws-1",
            "user_id": "u-1",
            "context": "",
            "known_columns": [],
        },
        {"configurable": {"api_key": "key"}},
    )

    assert result["final_code"] == 'result_df = conn.sql("select gross_margin from orders").fetchdf()'
    assert len(payloads) == 2
    assert "gross_margin" in payloads[1]["known_columns_json"]
    assert any(col["name"] == "gross_margin" for col in result["known_columns"])
