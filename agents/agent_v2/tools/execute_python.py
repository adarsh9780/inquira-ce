"""Workspace-kernel Python execution tool for agent-side validation/correction."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..events import emit_agent_event
from ..runtime import load_agent_runtime_config
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


async def execute_python(
    *,
    workspace_id: str,
    data_path: str | None,
    code: str,
    timeout: int = 90,
    explanation: str = "",
    emit_tool_events: bool = True,
) -> dict[str, Any]:
    _ = data_path
    started = time.perf_counter()
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

    if not str(workspace_id or "").strip():
        payload = _error("Missing workspace id.", "Missing workspace id")
        if emit_tool_events:
            emit_agent_event(
                "tool_result",
                {
                    "call_id": call_id,
                    "output": payload,
                    "status": "error",
                    "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
                },
            )
        return payload

    runtime = load_agent_runtime_config()
    url = (
        f"{runtime.backend_base_url}/api/v1/internal/agent/workspaces/{workspace_id}/execute"
    )
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if runtime.backend_shared_secret:
        headers["Authorization"] = f"Bearer {runtime.backend_shared_secret}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(max(5, int(timeout)) + 10.0)) as client:
            response = await client.post(
                url,
                json={
                    "code": str(code or ""),
                    "timeout": max(5, int(timeout)),
                },
                headers=headers,
            )
    except Exception as exc:
        payload = _error(
            "Workspace kernel execution request failed.",
            str(exc),
        )
        if emit_tool_events:
            emit_agent_event(
                "tool_result",
                {
                    "call_id": call_id,
                    "output": payload,
                    "status": "error",
                    "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
                },
            )
        return payload

    try:
        result = response.json() if response.content else {}
    except Exception:
        result = _error(
            "Workspace kernel returned an invalid execution payload.",
            response.text,
        )

    if response.status_code >= 400:
        detail = result.get("detail") if isinstance(result, dict) else None
        payload = _error(
            str(detail or f"Workspace kernel execution failed with status {response.status_code}."),
            str(detail or response.text or ""),
        )
        if emit_tool_events:
            emit_agent_event(
                "tool_result",
                {
                    "call_id": call_id,
                    "output": payload,
                    "status": "error",
                    "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
                },
            )
        return payload

    if not isinstance(result, dict):
        result = _error(
            "Workspace kernel returned an invalid execution payload.",
            str(result),
        )

    status = "success" if bool(result.get("success")) else "error"
    if emit_tool_events:
        emit_agent_event(
            "tool_result",
            {
                "call_id": call_id,
                "output": result,
                "status": status,
                "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
            },
        )
    return result
