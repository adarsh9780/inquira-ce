from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from agent_v2.coding_subagent import AnalysisOutput
from agent_v2.nodes import (
    _build_schema_search_queries,
    _normalize_broad_search_queries,
    _sanitize_tool_plan,
    analysis_generate_code_node,
)


def test_sanitize_tool_plan_forces_single_word_schema_queries() -> None:
    plan = _sanitize_tool_plan(
        [
            {
                "tool": "search_schema",
                "query": "The user has not specified which columns represent year",
                "limit": 20,
            }
        ],
        max_items=5,
    )

    assert plan
    assert all(item.get("tool") == "search_schema" for item in plan)
    assert all(" " not in str(item.get("query") or "") for item in plan)
    assert "year" in [str(item.get("query") or "") for item in plan]


def test_build_schema_search_queries_returns_keywords_not_sentences() -> None:
    queries = _build_schema_search_queries(
        base_query="bifurcate each bar by adding year as different colors",
        user_text="The user has not specified which dataset table should be used for year analysis",
        missing_context=["The user has not specified which columns represent year"],
        max_queries=6,
    )

    assert queries
    assert all(" " not in str(query or "") for query in queries)
    assert "year" in queries


def test_normalize_broad_search_queries_batches_single_word_keywords() -> None:
    queries = _normalize_broad_search_queries(
        query="top batsman by total runs in innings",
        queries=["powerplay strike rate", "economy"],
        max_items=8,
    )
    assert queries
    assert all(" " not in str(item or "") for item in queries)
    assert "batsman" in queries
    assert "runs" in queries
    assert any(item in queries for item in ["powerplay", "economy"])


@pytest.mark.asyncio
async def test_analysis_generate_code_reuses_enriched_sample_data_without_duplicate_sampling(
    monkeypatch,
) -> None:
    enriched_sample = {"rows": [{"year": 2024}], "columns": ["year"], "row_count": 1}
    calls: dict[str, object] = {"sample_data_calls": 0, "sample_json": ""}

    def fake_sample_data(**_kwargs):
        calls["sample_data_calls"] = int(calls["sample_data_calls"]) + 1
        return {"rows": [], "columns": [], "row_count": 0}

    async def fake_ainvoke_coding_chain(**kwargs):
        calls["sample_json"] = str(kwargs.get("sample_json") or "")
        return AnalysisOutput(
            code="print('ok')",
            explanation="done",
            output_contract=[],
            search_schema_queries=[],
            selected_tables=[],
            joins_used=False,
        )

    monkeypatch.setattr("agent_v2.nodes.sample_data", fake_sample_data)
    monkeypatch.setattr("agent_v2.nodes._get_model", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("agent_v2.nodes.build_coding_chain", lambda **_kwargs: object())
    monkeypatch.setattr("agent_v2.nodes.ainvoke_coding_chain", fake_ainvoke_coding_chain)

    result = await analysis_generate_code_node(
        {
            "analysis_context": {
                "messages": [HumanMessage(content="show yearly trend")],
                "data_path": "/tmp/ws.duckdb",
                "table_names": ["sales"],
                "schema_summary": "",
                "sample_table": "sales",
                "context": "",
            },
            "known_columns": [],
            "attempt_counters": {"generation": 0},
            "enrichment_results": {"sample_data": enriched_sample},
        },
        {"configurable": {}},
    )

    assert calls["sample_data_calls"] == 0
    assert '"year": 2024' in str(calls["sample_json"])
    assert result.get("candidate_code") == "print('ok')"
