"""Local Python execution tool for agent-side validation/correction."""

from __future__ import annotations

import asyncio
import contextlib
import io
from pathlib import Path
from typing import Any

import duckdb

from ..events import emit_agent_event
from . import new_tool_call_id


def _error(message: str, stderr: str = "") -> dict[str, Any]:
    text = str(message or "Execution failed")
    return {
        "success": False,
        "error": text,
        "stdout": "",
        "stderr": stderr or text,
        "result": None,
        "result_type": None,
        "result_kind": "none",
        "result_name": None,
        "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        "artifacts": [],
    }


def _run_code(code: str, data_path: str) -> dict[str, Any]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    globals_dict: dict[str, Any] = {}

    con = duckdb.connect(data_path, read_only=True)
    globals_dict["conn"] = con

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(code, globals_dict, globals_dict)  # noqa: S102
    except Exception as exc:  # noqa: BLE001
        con.close()
        return _error(str(exc), stderr.getvalue()) | {"stdout": stdout.getvalue()}
    finally:
        try:
            con.close()
        except Exception:
            pass

    return {
        "success": True,
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "error": None,
        "result": None,
        "result_type": None,
        "result_kind": "none",
        "result_name": None,
        "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        "artifacts": [],
    }


async def execute_python(
    *,
    workspace_id: str,
    data_path: str | None,
    code: str,
    timeout: int = 90,
    explanation: str = "",
    emit_tool_events: bool = True,
) -> dict[str, Any]:
    _ = workspace_id
    call_id = new_tool_call_id("execute_python")
    if emit_tool_events:
        emit_agent_event(
            "tool_call",
            {
                "tool": "execute_python",
                "args": {"timeout": timeout, "explanation": str(explanation or "").strip()},
                "call_id": call_id,
                "explanation": str(explanation or "").strip(),
            },
        )

    if not data_path:
        payload = _error("Missing workspace data path.", "Missing data path")
        if emit_tool_events:
            emit_agent_event(
                "tool_result",
                {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
            )
        return payload

    if not Path(data_path).expanduser().exists():
        payload = _error(
            "Workspace database is missing. Please re-create the workspace data by selecting the original dataset again.",
            f"Missing workspace database: {data_path}",
        )
        if emit_tool_events:
            emit_agent_event(
                "tool_result",
                {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
            )
        return payload

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_code, str(code or ""), str(data_path)),
            timeout=max(5, int(timeout)),
        )
    except TimeoutError:
        result = _error("Code execution timed out.", "Timed out")

    status = "success" if bool(result.get("success")) else "error"
    if emit_tool_events:
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": result, "status": status, "duration_ms": 1},
        )
    return result
