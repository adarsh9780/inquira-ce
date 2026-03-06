"""Silent Python execution tool for agent-side validation/correction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...agent.events import emit_agent_event
from ...services.code_executor import execute_code
from . import new_tool_call_id


async def execute_python(
    *,
    workspace_id: str,
    data_path: str | None,
    code: str,
    timeout: int = 90,
) -> dict[str, Any]:
    call_id = new_tool_call_id("execute_python")
    emit_agent_event(
        "tool_call",
        {"tool": "execute_python", "args": {"timeout": timeout}, "call_id": call_id},
    )

    if not data_path:
        payload = {"success": False, "error": "Missing workspace data path.", "stdout": "", "stderr": "Missing data path"}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload
    if not Path(data_path).expanduser().exists():
        payload = {
            "success": False,
            "error": (
                "Workspace database is missing. "
                "Please re-create the workspace data by selecting the original dataset again."
            ),
            "stdout": "",
            "stderr": f"Missing workspace database: {data_path}",
        }
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    result = await execute_code(
        code=code,
        timeout=max(5, int(timeout)),
        workspace_id=workspace_id,
        workspace_duckdb_path=data_path,
    )
    status = "success" if bool(result.get("success")) else "error"
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": result, "status": status, "duration_ms": 1},
    )
    return result
