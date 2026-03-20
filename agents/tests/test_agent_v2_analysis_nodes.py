from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from agent_v2.nodes import (
    _ASSESS_CONTEXT_PROMPT,
    analysis_collect_context_node,
    analysis_enrich_context_node,
    analysis_generate_code_node,
    analysis_retry_decider_node,
)
from agent_v2.coding_subagent import AnalysisOutput


@pytest.mark.asyncio
async def test_analysis_enrich_context_updates_known_columns_from_search_schema(monkeypatch) -> None:
    def fake_search_schema(**_kwargs):
        return {
            "query": "customer",
            "table_name": "",
            "match_count": 1,
            "columns": [
                {"table_name": "orders", "name": "customer_id", "dtype": "VARCHAR", "description": ""},
            ],
        }

    monkeypatch.setattr("agent_v2.nodes.search_schema", fake_search_schema)

    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {
            "data_path": "",
            "table_names": ["orders"],
            "sample_table": "orders",
        },
        "tool_plan": [{"tool": "search_schema", "query": "customer", "limit": 20}],
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "messages": [HumanMessage(content="show customer totals")],
    }

    result = await analysis_enrich_context_node(state, {"configurable": {}})
    known = result.get("known_columns") or []
    assert any(str(item.get("name") or "").strip().lower() == "customer_id" for item in known)


@pytest.mark.asyncio
async def test_analysis_enrich_context_ignores_pip_install_tool_plan_entry() -> None:
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {"data_path": "", "table_names": [], "sample_table": ""},
        "tool_plan": [
            {"tool": "pip_install", "packages": ["pandas"]},
            {"tool": "search_schema", "query": "revenue"},
        ],
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
    }

    result = await analysis_enrich_context_node(state, {"configurable": {}})
    enrichment_results = result.get("enrichment_results") or {}
    assert "pip_install" not in enrichment_results


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
async def test_analysis_enrich_context_passes_workspace_schema_and_fallback_keyword(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_search_schema(**kwargs):
        calls.append(kwargs)
        query = str(kwargs.get("query") or "")
        if query == "batsman top runs players":
            return {"query": query, "table_name": "", "match_count": 0, "columns": []}
        if query == "batsman":
            return {
                "query": query,
                "table_name": "",
                "match_count": 1,
                "columns": [{"table_name": "batting", "name": "batsman", "dtype": "VARCHAR", "description": "Player"}],
            }
        return {"query": query, "table_name": "", "match_count": 0, "columns": []}

    monkeypatch.setattr("agent_v2.nodes.search_schema", fake_search_schema)

    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "known_columns": [],
        "analysis_context": {
            "data_path": "",
            "table_names": ["batting"],
            "sample_table": "batting",
            "workspace_schema": {"tables": [{"table_name": "batting", "columns": [{"name": "batsman"}]}]},
        },
        "tool_plan": [{"tool": "search_schema", "query": "batsman top runs players", "limit": 20}],
        "attempt_counters": {"enrichment": 0, "max_tool_calls": 5},
        "messages": [HumanMessage(content="top batsman")],
    }

    result = await analysis_enrich_context_node(state, {"configurable": {}})
    known = result.get("known_columns") or []
    assert any(str(item.get("name") or "").strip().lower() == "batsman" for item in known)
    assert isinstance(calls[0].get("schema"), dict)
    assert any(str(call.get("query") or "") == "batsman" for call in calls)


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
    tool_plan = result.get("tool_plan") or []
    assert isinstance(tool_plan, list)
    assert tool_plan and tool_plan[0].get("tool") == "search_schema"
    assert tool_plan[0].get("query") == "batsman"
