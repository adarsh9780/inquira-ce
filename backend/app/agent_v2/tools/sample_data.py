"""Workspace dataset sampling tool."""

from __future__ import annotations

import duckdb

from ..events import emit_agent_event
from . import new_tool_call_id


def sample_data(*, data_path: str | None, table_name: str | None, limit: int = 5) -> dict:
    call_id = new_tool_call_id("sample_data")
    safe_limit = max(1, min(50, int(limit)))
    emit_agent_event(
        "tool_call",
        {
            "tool": "sample_data",
            "args": {
                "table_name": table_name or "",
                "limit": safe_limit,
            },
            "call_id": call_id,
        },
    )

    if not data_path or not table_name:
        output = {"rows": [], "columns": [], "row_count": 0}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": output, "status": "success", "duration_ms": 1},
        )
        return output

    query = f'SELECT * FROM "{table_name}" LIMIT {safe_limit}'
    try:
        con = duckdb.connect(data_path, read_only=True)
        try:
            df = con.execute(query).fetchdf()
        finally:
            con.close()

        output = {
            "rows": df.head(safe_limit).to_dict(orient="records"),
            "columns": [str(c) for c in list(df.columns)],
            "row_count": int(len(df)),
        }
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": output, "status": "success", "duration_ms": 3},
        )
        return output
    except Exception as exc:
        emit_agent_event(
            "tool_result",
            {
                "call_id": call_id,
                "output": {"error": str(exc)},
                "status": "error",
                "duration_ms": 3,
            },
        )
        return {"rows": [], "columns": [], "row_count": 0, "error": str(exc)}
