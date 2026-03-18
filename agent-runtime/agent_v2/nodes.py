from __future__ import annotations

import uuid
from typing import Any

from .coding_subagent import generate_code_plan
from .tools import analyze_table, finish


def build_result(*, question: str, table_name: str) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    plan = generate_code_plan(question, table_name)
    tool_output = analyze_table(table_name)
    explanation = (
        f"I generated a starter analysis for `{table_name}` and selected a preview slice."
    )
    final = finish(explanation, metadata={"plan": plan})
    return {
        "run_id": run_id,
        "route": "analysis",
        "metadata": {
            "is_safe": True,
            "is_relevant": True,
            "tables_used": [str(table_name or "").strip() or "data"],
            "joins_used": False,
            "join_keys": [],
            **(final.get("metadata") or {}),
        },
        "final_code": tool_output["code"],
        "final_explanation": final["final_explanation"],
        "result_explanation": final["final_explanation"],
        "code_explanation": "Runs a table preview query using backend-provided DuckDB connection `conn`.",
        "output_contract": tool_output["output_contract"],
        "messages": [],
    }
