"""Schema inspection tool."""

from __future__ import annotations

from typing import Any

from ...agent.events import emit_agent_event
from . import new_tool_call_id


def inspect_schema(*, schema: dict[str, Any], table_name: str | None) -> dict[str, Any]:
    call_id = new_tool_call_id("inspect_schema")
    emit_agent_event(
        "tool_call",
        {
            "tool": "inspect_schema",
            "args": {"table_name": table_name or "", "column_count": len(schema.get("columns", []))},
            "call_id": call_id,
        },
    )

    columns = schema.get("columns", [])
    normalized = [col for col in columns if isinstance(col, dict)]
    result = {
        "table_name": table_name or str(schema.get("table_name") or ""),
        "column_count": len(normalized),
        "columns": [
            {
                "name": str(col.get("name") or ""),
                "dtype": str(col.get("dtype") or col.get("type") or ""),
            }
            for col in normalized[:50]
        ],
    }
    emit_agent_event(
        "tool_result",
        {
            "call_id": call_id,
            "output": result,
            "status": "success",
            "duration_ms": 1,
        },
    )
    return result
