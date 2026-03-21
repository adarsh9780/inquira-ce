from __future__ import annotations

import pytest

from agent_v2.tools.execute_python import execute_python
from agent_v2.tools.search_schema import search_schema


def test_search_schema_tool_call_event_includes_explanation(monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        "agent_v2.tools.search_schema.emit_agent_event",
        lambda event, payload: captured.append((event, payload)),
    )

    result = search_schema(
        schema={
            "tables": [
                {
                    "table_name": "orders",
                    "columns": [{"name": "revenue", "dtype": "DOUBLE", "description": "Order revenue"}],
                }
            ]
        },
        data_path=None,
        table_names=["orders"],
        query="revenue",
        queries=["revenue"],
        table_name="orders",
        max_results=10,
        explanation="I need schema matches before I write code.",
        emit_tool_events=True,
    )

    assert result["match_count"] == 1
    assert captured[0][0] == "tool_call"
    assert captured[0][1]["explanation"] == "I need schema matches before I write code."


@pytest.mark.asyncio
async def test_execute_python_tool_call_event_includes_explanation(monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        "agent_v2.tools.execute_python.emit_agent_event",
        lambda event, payload: captured.append((event, payload)),
    )
    monkeypatch.setattr(
        "agent_v2.tools.execute_python._run_code",
        lambda code, data_path: {
            "success": True,
            "stdout": "ok",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "result_kind": "none",
            "result_name": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
        },
    )

    result = await execute_python(
        workspace_id="ws1",
        data_path=__file__,
        code="print('ok')",
        timeout=5,
        explanation="I have candidate code and need to verify it runs.",
        emit_tool_events=True,
    )

    assert result["success"] is True
    assert captured[0][0] == "tool_call"
    assert captured[0][1]["explanation"] == "I have candidate code and need to verify it runs."
