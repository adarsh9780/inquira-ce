from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from agent_v2.nodes import (
    analysis_enrich_context_node,
    analysis_retry_decider_node,
)


@pytest.mark.asyncio
async def test_analysis_enrich_context_updates_known_columns_from_search_schema() -> None:
    state = {
        "workspace_id": "ws1",
        "user_id": "u1",
        "active_schema": {
            "tables": [
                {
                    "table_name": "orders",
                    "columns": [
                        {"name": "order_id", "dtype": "INTEGER"},
                        {"name": "customer_id", "dtype": "VARCHAR"},
                    ],
                }
            ]
        },
        "known_columns": [],
        "analysis_context": {
            "data_path": "",
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
        "active_schema": {},
        "known_columns": [],
        "analysis_context": {"data_path": "", "sample_table": ""},
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
