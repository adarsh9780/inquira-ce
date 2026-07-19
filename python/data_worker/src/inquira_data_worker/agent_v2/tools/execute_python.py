"""Workspace-kernel execution tool bound to the Go-managed Python worker."""

from __future__ import annotations

import inspect
import time
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from ..events import emit_agent_event
from . import new_tool_call_id


LocalExecutor = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]
_LOCAL_EXECUTOR: ContextVar[LocalExecutor | None] = ContextVar(
    "_inquira_agent_local_executor",
    default=None,
)


def set_local_executor(executor: LocalExecutor):
    return _LOCAL_EXECUTOR.set(executor)


def reset_local_executor(token: Any) -> None:
    _LOCAL_EXECUTOR.reset(token)


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
        "timed_out": False,
    }


async def execute_python(
    *,
    workspace_id: str,
    data_path: str | None,
    code: str,
    timeout: int = 90,
    output_contract: list[dict[str, str]] | None = None,
    explanation: str = "",
    emit_tool_events: bool = True,
    run_id: str | None = None,
    conversation_id: str | None = None,
    turn_id: str | None = None,
    artifact_dir: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    call_id = new_tool_call_id("execute_python")
    if emit_tool_events:
        emit_agent_event(
            "tool_call",
            {
                "tool": "execute_python",
                "args": {
                    "timeout": timeout,
                    "explanation": str(explanation or "").strip(),
                },
                "call_id": call_id,
                "explanation": str(explanation or "").strip(),
            },
        )

    if not str(workspace_id or "").strip():
        result = _error("Missing workspace id.", "Missing workspace id")
    elif not str(code or "").strip():
        result = _error("Missing Python code.", "Missing Python code")
    else:
        executor = _LOCAL_EXECUTOR.get()
        if not callable(executor):
            result = _error(
                "The managed workspace kernel is unavailable.",
                "No local workspace-kernel executor is bound to this agent request.",
            )
        else:
            try:
                value = executor(
                    workspace_id=str(workspace_id),
                    database_path=str(data_path or ""),
                    code=str(code),
                    timeout_seconds=max(1, int(timeout)),
                    output_contract=output_contract or [],
                    run_id=str(run_id or ""),
                    conversation_id=str(conversation_id or ""),
                    turn_id=str(turn_id or ""),
                    artifact_dir=str(artifact_dir or ""),
                )
                result = await value if inspect.isawaitable(value) else value
                if not isinstance(result, dict):
                    result = _error("Workspace kernel returned an invalid execution payload.")
            except Exception as exc:
                result = _error("Workspace kernel execution failed.", str(exc))

    if emit_tool_events:
        emit_agent_event(
            "tool_result",
            {
                "call_id": call_id,
                "output": result,
                "status": "success" if bool(result.get("success")) else "error",
                "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
            },
        )
    return result
