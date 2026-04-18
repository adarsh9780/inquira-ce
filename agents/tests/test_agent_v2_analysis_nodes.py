from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate

from agent_v2.nodes import (
    _ASSESS_CONTEXT_PROMPT,
    _CONTEXT_ENRICHMENT_TOOL_PROMPT,
    _build_context_enrichment_user_prompt,
    _is_recoverable_structured_output_error,
    analysis_assess_context_node,
    analysis_collect_context_node,
    analysis_prepare_sample_to_next,
    analysis_prepare_sample_tool_node,
    analysis_request_execute_tool_node,
    analysis_request_validate_result_tool_node,
    analysis_enrich_to_next,
    analysis_enrich_context_node,
    analysis_runtime_tools_node,
    analysis_finalize_context_enrichment_node,
    analysis_generate_code_node,
    analysis_generate_to_next,
    analysis_runtime_tools_to_next,
    analysis_validate_result_node,
    analysis_validate_to_next,
    analysis_retry_decider_node,
    _filter_redundant_context_tools,
    ContextEnrichmentPlan,
    StructuredToolCall,
)
from agent_v2.coding_subagent.schema import AnalysisOutput


@pytest.mark.asyncio
async def test_analysis_enrich_context_node_produces_structured_pending_tools(monkeypatch) -> None:
    class _FakePrompt:
        def __or__(self, _other):
            return object()

    class _FakeModel:
        def with_structured_output(self, _schema):
            return self

    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: _FakeModel())
    monkeypatch.setattr("agent_v2.nodes.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())
    
    async def fake_ainvoke(*_args, **_kwargs):
        return ContextEnrichmentPlan(
            enough_context=False,
            missing_context=["matching columns"],
            notes="Need schema matches first.",
            tools=[
                StructuredToolCall(
                    tool="search_schema",
                    args={"queries": ["customer", "amount"], "table_name": "orders", "limit": 10},
                    explanation="I have the user goal, so I’m checking schema matches before writing code.",
                )
            ],
        )

    monkeypatch.setattr("agent_v2.nodes._ainvoke_structured_chain", fake_ainvoke)
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {
            "data_path": "",
            "table_names": ["orders"],
            "sample_table": "orders",
            "user_text": "show customer totals",
            "schema_summary": "orders(customer_id, amount)",
        },
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "messages": [HumanMessage(content="show customer totals")],
    }

    result = await analysis_enrich_context_node(state, {"configurable": {}})
    pending_tools = result.get("pending_tools") or []
    assert len(pending_tools) == 1
    assert pending_tools[0]["tool"] == "search_schema"
    assert pending_tools[0]["args"]["queries"] == ["customer", "amount"]
    assert pending_tools[0]["explanation"] == (
        "I have the user goal, so I’m checking schema matches before writing code."
    )
    tool_messages = result.get("analysis_tool_messages") or []
    assert len(tool_messages) == 1
    assert isinstance(tool_messages[0], AIMessage)


@pytest.mark.asyncio
async def test_analysis_enrich_context_node_recovers_from_injected_sse_json_error(monkeypatch) -> None:
    class _FakePrompt:
        def __or__(self, _other):
            return object()

    class _FakeModel:
        def with_structured_output(self, _schema):
            return self

    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: _FakeModel())
    monkeypatch.setattr("agent_v2.nodes.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())

    async def fake_ainvoke(*_args, **_kwargs):
        raise RuntimeError("JSON error injected into SSE stream")

    monkeypatch.setattr("agent_v2.nodes._ainvoke_structured_chain", fake_ainvoke)
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [{"table_name": "orders", "name": "amount"}],
        "context_sufficiency": {"missing_context": ["matching columns"]},
        "analysis_context": {
            "data_path": "",
            "table_names": ["orders"],
            "sample_table": "orders",
            "user_text": "show customer totals",
            "schema_summary": "orders(customer_id, amount)",
        },
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "messages": [HumanMessage(content="show customer totals")],
    }

    result = await analysis_enrich_context_node(state, {"configurable": {}})
    assert result.get("pending_tools") == []
    tool_messages = result.get("analysis_tool_messages") or []
    assert len(tool_messages) == 1
    assert "Structured enrichment planning failed" in str(tool_messages[0].content)


def test_recoverable_structured_output_error_matches_injected_sse_json_error() -> None:
    assert _is_recoverable_structured_output_error(RuntimeError("JSON error injected into SSE stream")) is True
    assert _is_recoverable_structured_output_error(ValueError("expected value at line 3 column 1")) is True


def test_context_enrichment_prompt_includes_prior_search_context() -> None:
    rendered = _build_context_enrichment_user_prompt(
        user_text="top scorers",
        conversation_memory="Earlier we focused on batting metrics.",
        schema_summary="batting table",
        known_columns=[],
        missing_context=["columns"],
        retry_feedback="",
        enrichment_hints=["runs", "batsman"],
        prior_search_summary="search_schema[runs,batsman] -> matches=4",
        tool_budget_remaining=3,
    )
    assert "Prior search context:" in rendered
    assert "matches=4" in rendered


def test_context_enrichment_prompt_requires_tool_explanations() -> None:
    assert "what I got, what I will do next" in _CONTEXT_ENRICHMENT_TOOL_PROMPT


def test_context_enrichment_prompt_escapes_literal_tool_examples() -> None:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _CONTEXT_ENRICHMENT_TOOL_PROMPT),
            ("human", "{tool_request_prompt}"),
        ]
    )
    assert prompt.input_variables == ["tool_request_prompt"]


def test_context_enrichment_plan_schema_uses_openai_strict_tool_args() -> None:
    schema = ContextEnrichmentPlan.model_json_schema()
    defs = schema["$defs"]
    tool_call = defs["StructuredToolCall"]
    tool_args = defs["StructuredToolArgs"]

    assert tool_call["additionalProperties"] is False
    assert tool_args["additionalProperties"] is False
    assert "oneOf" not in schema["properties"]["tools"]["items"]
    assert "discriminator" not in schema["properties"]["tools"]["items"]
    assert set(tool_call["required"]) == set(tool_call["properties"])
    assert set(tool_args["required"]) == set(tool_args["properties"])
    assert "default" not in str(tool_args)


@pytest.mark.asyncio
async def test_analysis_enrich_to_next_routes_to_custom_tool_node_when_pending_tools_exist() -> None:
    state = {
        "pending_tools": [
            {"tool": "search_schema", "args": {"query": "runs"}, "explanation": "I need schema matches next."}
        ]
    }
    assert analysis_enrich_to_next(state) == "analysis_enrich_context_tools"


@pytest.mark.asyncio
async def test_analysis_enrich_to_next_routes_to_finalize_without_tool_calls() -> None:
    state = {"analysis_tool_messages": [AIMessage(content='{"enough_context": true, "missing_context": []}')]}
    assert analysis_enrich_to_next(state) == "analysis_finalize_context_enrichment"


@pytest.mark.asyncio
async def test_analysis_finalize_context_enrichment_merges_search_tool_results() -> None:
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {
            "data_path": "",
            "table_names": ["orders"],
            "sample_table": "orders",
            "user_text": "show revenue by customer",
        },
        "analysis_tool_messages": [
            ToolMessage(
                name="search_schema",
                tool_call_id="c1",
                content='{"query":"revenue","columns":[{"table_name":"orders","name":"customer_id","dtype":"VARCHAR","description":"customer key"}]}',
            ),
            AIMessage(content='{"enough_context": true, "missing_context": [], "notes": "ready"}'),
        ],
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "enrichment_tool_cursor": 0,
    }

    result = await analysis_finalize_context_enrichment_node(state, {"configurable": {}})
    known = result.get("known_columns") or []
    assert any(str(item.get("name") or "").strip().lower() == "customer_id" for item in known)
    enrichment_results = result.get("enrichment_results") or {}
    assert "search_schema" in enrichment_results
    assert result.get("context_sufficiency", {}).get("enough_context") is True


@pytest.mark.asyncio
async def test_analysis_prepare_sample_tool_creates_pending_runtime_tool_when_sample_missing() -> None:
    state = {
        "analysis_context": {"sample_table": "orders"},
        "enrichment_results": {},
    }
    result = await analysis_prepare_sample_tool_node(state, {"configurable": {}})
    pending_tools = result.get("pending_tools") or []
    assert len(pending_tools) == 1
    assert pending_tools[0].get("tool") == "sample_data_runtime"
    assert pending_tools[0].get("explanation") == (
        "I have the candidate table, so I’m sampling a few rows before generating code."
    )


@pytest.mark.asyncio
async def test_analysis_request_execute_tool_includes_short_explanation() -> None:
    state = {
        "candidate_code": "print('ok')",
        "attempt_counters": {"execution": 0},
    }
    result = await analysis_request_execute_tool_node(state, {"configurable": {}})
    pending_tools = result.get("pending_tools") or []
    assert pending_tools[0].get("explanation") == (
        "I have executable code, so I’m running it now and will inspect the result next."
    )


@pytest.mark.asyncio
async def test_analysis_request_validate_result_tool_includes_short_explanation() -> None:
    state = {
        "execution_result": {"success": True, "stdout": "done"},
    }
    result = await analysis_request_validate_result_tool_node(state, {"configurable": {}})
    pending_tools = result.get("pending_tools") or []
    assert pending_tools[0].get("explanation") == (
        "I have the runtime output, so I’m checking whether it is useful enough to return."
    )


def test_analysis_prepare_sample_to_next_routes_to_runtime_tools_when_pending_call() -> None:
    state = {
        "pending_tools": [{"tool": "sample_data_runtime", "args": {}, "explanation": "Sampling rows next."}]
    }
    assert analysis_prepare_sample_to_next(state) == "analysis_runtime_tools"


@pytest.mark.asyncio
async def test_analysis_runtime_tools_node_emits_tool_messages_and_trace_hooks(monkeypatch) -> None:
    events: list[tuple[str, dict]] = []
    span_events: list[tuple[str, str, str, str]] = []

    monkeypatch.setattr(
        "agent_v2.nodes.sample_data",
        lambda **_kwargs: {"rows": [{"customer_id": "c1"}], "columns": ["customer_id"], "row_count": 1},
    )
    monkeypatch.setattr(
        "agent_v2.nodes.emit_agent_event",
        lambda event, payload: events.append((event, payload)),
    )
    monkeypatch.setattr(
        "agent_v2.nodes._record_tool_span_event",
        lambda **kwargs: span_events.append(
            (
                str(kwargs.get("event_name") or ""),
                str(kwargs.get("tool_name") or ""),
                str(kwargs.get("call_id") or ""),
                str(kwargs.get("status") or ""),
            )
        ),
    )
    state = {
        "analysis_context": {"data_path": "/tmp/ws.db", "sample_table": "orders"},
        "pending_tools": [
            {
                "tool": "sample_data_runtime",
                "args": {"table_name": "orders", "limit": 5},
                "explanation": "I found the target table, so I’m sampling rows next.",
            }
        ],
    }

    result = await analysis_runtime_tools_node(state, {"configurable": {}})
    runtime_messages = result.get("analysis_runtime_tool_messages") or []
    assert len(runtime_messages) == 1
    assert isinstance(runtime_messages[0], ToolMessage)
    payload = runtime_messages[0].content
    assert "customer_id" in str(payload)
    assert result.get("pending_tools") == []
    assert [event for event, _payload in events] == ["tool_call", "tool_result"]
    assert [item[0] for item in span_events] == ["agent.tool_call", "agent.tool_result"]


def test_analysis_runtime_tools_to_next_routes_by_stage() -> None:
    assert analysis_runtime_tools_to_next({"runtime_tool_stage": "sample"}) == "analysis_capture_sample_tool_result"
    assert analysis_runtime_tools_to_next({"runtime_tool_stage": "execute"}) == "analysis_capture_execute_tool_result"
    assert analysis_runtime_tools_to_next({"runtime_tool_stage": "validate"}) == "analysis_validate_result"


@pytest.mark.asyncio
async def test_analysis_retry_decider_routes_context_gap_to_enrich() -> None:
    state = {
        "candidate_code": "print('x')",
        "execution_result": {"success": False, "error": "Column customer_name not found"},
        "attempt_counters": {"execution": 1, "generation": 1, "max_code_executions": 3},
    }
    result = await analysis_retry_decider_node(state, {"configurable": {}})
    assert result.get("retry_target") == "analysis_enrich_context"


@pytest.mark.asyncio
async def test_analysis_retry_decider_routes_code_bug_to_regenerate() -> None:
    state = {
        "candidate_code": "print(undefined_var)",
        "execution_result": {"success": False, "error": "NameError: name 'undefined_var' is not defined"},
        "attempt_counters": {"execution": 1, "generation": 1, "max_code_executions": 3},
    }
    result = await analysis_retry_decider_node(state, {"configurable": {}})
    assert result.get("retry_target") == "analysis_generate_code"


@pytest.mark.asyncio
async def test_analysis_retry_decider_routes_non_retriable_to_failure() -> None:
    state = {
        "candidate_code": "print('x')",
        "execution_result": {"success": False, "error": "Workspace database is missing"},
        "attempt_counters": {"execution": 1, "generation": 1, "max_code_executions": 3},
    }
    result = await analysis_retry_decider_node(state, {"configurable": {}})
    assert result.get("retry_target") == "analysis_finalize_failure"


def test_assess_context_prompt_escapes_literal_tool_examples() -> None:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _ASSESS_CONTEXT_PROMPT),
            ("human", "User question: {user_text}"),
        ]
    )
    assert "tool" not in prompt.input_variables


@pytest.mark.asyncio
async def test_analysis_collect_context_does_not_persist_preferred_table_field() -> None:
    state = {
        "messages": [HumanMessage(content="show top scorers")],
        "table_names": ["batting", "matches"],
        "known_columns": [],
        "data_path": "/tmp/ws.db",
    }
    result = await analysis_collect_context_node(state, {"configurable": {}})
    analysis_context = result.get("analysis_context") if isinstance(result, dict) else {}
    assert isinstance(analysis_context, dict)
    assert "preferred_table" not in analysis_context


@pytest.mark.asyncio
async def test_analysis_collect_context_resets_enrichment_loop_state() -> None:
    state = {
        "messages": [HumanMessage(content="show top scorers")],
        "table_names": ["batting"],
        "known_columns": [],
        "data_path": "/tmp/ws.db",
        "analysis_tool_messages": [AIMessage(content="old", id="old-ai-message")],
        "retry_feedback": "stale retry",
        "enrichment_results": {"search_schema": [{"query": "runs"}]},
        "enrichment_tool_cursor": 9,
    }
    result = await analysis_collect_context_node(state, {"configurable": {}})
    reset_messages = result.get("analysis_tool_messages") or []
    assert len(reset_messages) == 1
    assert isinstance(reset_messages[0], RemoveMessage)
    assert result.get("retry_feedback") == ""
    assert result.get("enrichment_results") == {}
    assert result.get("enrichment_tool_cursor") == 0


@pytest.mark.asyncio
async def test_analysis_collect_context_includes_table_and_column_descriptions() -> None:
    state = {
        "messages": [HumanMessage(content="show top scorers")],
        "table_names": ["batting"],
        "known_columns": [],
        "data_path": "/tmp/ws.db",
        "workspace_schema": {
            "tables": [
                {
                    "table_name": "batting",
                    "context": "Batting summary for all matches.",
                    "columns": [
                        {"name": "batsman", "description": "Player name"},
                        {"name": "runs", "description": "Runs scored"},
                    ],
                }
            ]
        },
    }
    result = await analysis_collect_context_node(state, {"configurable": {}})
    analysis_context = result.get("analysis_context") if isinstance(result, dict) else {}
    summary = str((analysis_context or {}).get("schema_summary") or "")
    assert "Batting summary for all matches." in summary
    assert "batsman" in summary
    assert "runs" in summary


@pytest.mark.asyncio
async def test_analysis_finalize_context_enrichment_persists_memory_from_chunk_results(
    tmp_path,
) -> None:
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.write_text("", encoding="utf-8")
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {
            "data_path": str(workspace_db),
            "table_names": ["ball_by_ball"],
            "sample_table": "ball_by_ball",
            "user_text": "top 10 batsman",
        },
        "analysis_tool_messages": [
            ToolMessage(
                name="scan_schema_chunks",
                tool_call_id="c2",
                content=(
                    '{"query_terms":["batsman"],"relevant_tables":[{"table_name":"ball_by_ball","context":"Ball-level cricket data","score":6}],'
                    '"columns":[{"table_name":"ball_by_ball","name":"batsman","dtype":"VARCHAR","description":"Batter name"}]}'
                ),
            ),
            AIMessage(content='{"enough_context": true, "missing_context": [], "notes": "ready"}'),
        ],
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "enrichment_tool_cursor": 0,
    }

    result = await analysis_finalize_context_enrichment_node(state, {"configurable": {}})
    memory_path = str(result.get("schema_memory_path") or "").strip()
    assert memory_path.endswith("context/schema_analysis_memory.md")
    rendered = (tmp_path / "context" / "schema_analysis_memory.md").read_text(encoding="utf-8")
    assert "ball_by_ball" in rendered
    assert "batsman" in rendered


@pytest.mark.asyncio
async def test_analysis_generate_code_requests_schema_enrichment_when_query_is_in_code(monkeypatch) -> None:
    monkeypatch.setattr("agent_v2.nodes.sample_data", lambda **_kwargs: [])
    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("agent_v2.nodes.build_coding_chain", lambda **_kwargs: object())

    async def fake_ainvoke_coding_chain(**_kwargs):
        return AnalysisOutput(
            code='search_schema_queries = ["batsman"]',
            explanation="Need schema",
            output_contract=[],
            search_schema_queries=[],
            selected_tables=[],
            joins_used=False,
        )

    monkeypatch.setattr("agent_v2.nodes.ainvoke_coding_chain", fake_ainvoke_coding_chain)

    state = {
        "analysis_context": {
            "messages": [HumanMessage(content="top batsman by runs")],
            "data_path": "/tmp/ws.db",
            "table_names": ["batting"],
            "schema_summary": "",
            "sample_table": "",
            "context": "",
        },
        "known_columns": [],
        "attempt_counters": {"generation": 0},
    }

    result = await analysis_generate_code_node(state, {"configurable": {}})
    assert result.get("candidate_code") == ""
    assert result.get("retry_target") == "analysis_enrich_context"
    hints = result.get("enrichment_hints") or []
    assert isinstance(hints, list)
    assert hints and hints[0] == "batsman"


@pytest.mark.asyncio
async def test_analysis_generate_code_stops_schema_enrichment_loop_at_generation_cap(monkeypatch) -> None:
    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("agent_v2.nodes.build_coding_chain", lambda **_kwargs: object())

    async def fake_ainvoke_coding_chain(**_kwargs):
        return AnalysisOutput(
            code='search_schema_queries = ["runs"]',
            explanation="Need more schema",
            output_contract=[],
            search_schema_queries=["runs"],
            selected_tables=[],
            joins_used=False,
        )

    monkeypatch.setattr("agent_v2.nodes.ainvoke_coding_chain", fake_ainvoke_coding_chain)

    state = {
        "analysis_context": {
            "messages": [HumanMessage(content="show top runs")],
            "data_path": "/tmp/ws.db",
            "table_names": ["batting"],
            "schema_summary": "",
            "sample_table": "",
            "context": "",
        },
        "known_columns": [],
        "enrichment_results": {"sample_data": {"rows": [], "columns": [], "row_count": 0}},
        "attempt_counters": {"generation": 2, "max_code_executions": 3},
    }

    result = await analysis_generate_code_node(state, {"configurable": {}})
    assert result.get("candidate_code") == ""
    assert result.get("retry_target") == ""
    assert int((result.get("attempt_counters") or {}).get("generation") or 0) == 3
    assert analysis_generate_to_next(result) == "analysis_retry_decider"


@pytest.mark.asyncio
async def test_analysis_collect_context_reads_schema_memory(tmp_path) -> None:
    workspace_db = tmp_path / "workspace.duckdb"
    workspace_db.write_text("", encoding="utf-8")
    memory_dir = tmp_path / "context"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_file = memory_dir / "schema_analysis_memory.md"
    memory_file.write_text("# Schema Analysis Memory\n\n- Question focus: top batsman\n", encoding="utf-8")

    state = {
        "messages": [HumanMessage(content="show top scorers")],
        "table_names": ["batting"],
        "known_columns": [],
        "data_path": str(workspace_db),
    }
    result = await analysis_collect_context_node(state, {"configurable": {}})
    analysis_context = result.get("analysis_context") if isinstance(result, dict) else {}
    assert isinstance(analysis_context, dict)
    assert "schema_memory" in analysis_context
    assert "Schema Analysis Memory" in str(analysis_context.get("schema_memory") or "")


@pytest.mark.asyncio
async def test_analysis_collect_context_adds_conversation_memory_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent_v2.nodes.load_agent_runtime_config",
        lambda: SimpleNamespace(
            max_tool_calls=5,
            max_code_executions=3,
            memory_max_recent_messages=3,
            memory_max_summary_tokens=400,
        ),
    )
    state = {
        "messages": [
            HumanMessage(content="Find yearly sales trend"),
            AIMessage(content="I will inspect schema first."),
            HumanMessage(content="Focus APAC region."),
            AIMessage(content="Noted, filtering APAC."),
            HumanMessage(content="Now compare with EMEA."),
        ],
        "table_names": ["sales"],
        "known_columns": [],
        "data_path": "/tmp/ws.db",
    }
    result = await analysis_collect_context_node(state, {"configurable": {}})
    analysis_context = result.get("analysis_context") or {}
    summary = str(analysis_context.get("conversation_memory") or "")
    recent_messages = analysis_context.get("messages") or []

    assert "User requests:" in summary
    assert "Find yearly sales trend" in summary
    assert len(recent_messages) <= 3


def test_filter_redundant_context_tools_skips_duplicate_search_and_sample_calls() -> None:
    existing_results = {
        "search_schema": [
            {"query": "runs", "queries": ["runs", "batsman"]},
        ],
        "scan_schema_chunks": [
            {"query_terms": ["batsman", "runs"]},
        ],
        "sample_data": {"rows": [{"batsman": "A"}]},
    }
    tools = [
        {
            "tool": "search_schema",
            "args": {"query": "runs", "queries": ["runs", "batsman"], "limit": 20},
            "explanation": "Duplicate lookup",
        },
        {
            "tool": "search_schema",
            "args": {"query": "economy", "queries": ["economy", "runs"], "limit": 20},
            "explanation": "Need unseen metric",
        },
        {
            "tool": "scan_schema_chunks",
            "args": {"query_terms": ["runs", "batsman"], "chunk_size": 4, "max_chunks": 12},
            "explanation": "Duplicate chunk scan",
        },
        {
            "tool": "sample_data",
            "args": {"table_name": "ball_by_ball", "limit": 5},
            "explanation": "Duplicate sample request",
        },
    ]

    filtered = _filter_redundant_context_tools(tools, existing_results)
    assert len(filtered) == 1
    assert filtered[0]["tool"] == "search_schema"
    assert filtered[0]["args"]["queries"] == ["economy"]


@pytest.mark.asyncio
async def test_analysis_validate_result_retries_when_execution_has_no_signal(monkeypatch) -> None:
    async def fake_validate_and_summarize_result(**_kwargs):
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "result_kind": "none",
            "artifact_count": 0,
            "artifacts": [],
        }

    async def fake_generate_result_explanations(**_kwargs):
        class _Payload:
            result_explanation = ""
            code_explanation = "No output"

        return _Payload()

    monkeypatch.setattr("agent_v2.nodes.validate_and_summarize_result", fake_validate_and_summarize_result)
    monkeypatch.setattr("agent_v2.nodes._generate_result_explanations", fake_generate_result_explanations)

    state = {
        "workspace_id": "ws1",
        "run_id": "r1",
        "execution_result": {"success": True, "stdout": "", "stderr": "", "artifacts": []},
        "analysis_context": {"user_text": "top batsman"},
        "candidate_code": "print('x')",
        "analysis_output": {"explanation": "explain"},
    }
    result = await analysis_validate_result_node(state, {"configurable": {}})
    assert result.get("retry_target") == "analysis_generate_code"
    assert analysis_validate_to_next(result) == "analysis_generate_code"


@pytest.mark.asyncio
async def test_analysis_assess_context_falls_back_when_length_limit_error(monkeypatch) -> None:
    class _LengthErr(Exception):
        pass

    async def fake_invoke(*_args, **_kwargs):
        raise _LengthErr("Could not parse response content as the length limit was reached")

    monkeypatch.setattr("agent_v2.nodes._ainvoke_structured_chain", fake_invoke)

    class _FakeChain:
        def __or__(self, _other):
            return self

        def with_structured_output(self, _schema):
            return self

    class _FakeModel:
        def with_structured_output(self, _schema):
            return _FakeChain()

    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: _FakeModel())
    monkeypatch.setattr("agent_v2.nodes.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakeChain())

    state = {
        "analysis_context": {
            "messages": [HumanMessage(content="give me top 10 batsman")],
            "user_text": "give me top 10 batsman",
            "schema_summary": "x" * 5000,
            "table_names": ["table_a"],
        },
        "known_columns": [],
    }
    result = await analysis_assess_context_node(state, {"configurable": {}})
    assert isinstance(result.get("tool_plan"), list)
    assert result.get("tool_plan")
    assert result.get("tool_plan")[0].get("tool") == "search_schema"


def test_analysis_validate_to_next_routes_to_failure_after_retry_cap() -> None:
    state = {
        "validation_outcome": {"status": "retry", "reason": "no output"},
        "attempt_counters": {"generation": 3, "max_code_executions": 3},
    }
    assert analysis_validate_to_next(state) == "analysis_finalize_failure"
