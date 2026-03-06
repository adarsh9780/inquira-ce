"""Restricted workspace bash tool with streamed progress events."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

from ...agent.events import emit_agent_event
from ...agent.registry import load_agent_runtime_config
from ...services.terminal_executor import stream_workspace_terminal_command
from . import new_tool_call_id


_BLOCKED_SYNTAX_RE = re.compile(r"(&&|\|\||;|>|<|`|\$\(|\r|\n)")


def _first_token(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except Exception:
        tokens = command.split()
    if not tokens:
        return ""
    return str(tokens[0]).strip().lower()


def _validate_command(command: str) -> str | None:
    normalized = str(command or "").strip()
    if not normalized:
        return "No command provided."
    if _BLOCKED_SYNTAX_RE.search(normalized):
        return "Blocked shell syntax in command."
    runtime = load_agent_runtime_config()
    allowlist = {cmd.lower() for cmd in runtime.bash_allowed_commands}
    token = _first_token(normalized)
    if token not in allowlist:
        return f"Command '{token or '<empty>'}' is not allowed."
    return None


async def run_bash(
    *,
    user_id: str,
    workspace_id: str,
    data_path: str | None,
    command: str,
    timeout: int = 60,
) -> dict[str, Any]:
    call_id = new_tool_call_id("bash")
    emit_agent_event(
        "tool_call",
        {"tool": "bash", "args": {"command": command}, "call_id": call_id},
    )

    validation_error = _validate_command(command)
    if validation_error:
        payload = {"error": validation_error, "stdout": "", "stderr": validation_error, "exit_code": 1}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    if not data_path:
        payload = {"error": "Missing workspace data path.", "stdout": "", "stderr": "Missing data path", "exit_code": 1}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    workspace_dir = str(Path(data_path).resolve().parent)
    final_result: dict[str, Any] | None = None
    async for event in stream_workspace_terminal_command(
        user_id=user_id,
        workspace_id=workspace_id,
        command=command,
        workspace_dir=workspace_dir,
        cwd=workspace_dir,
        timeout=max(5, int(timeout)),
    ):
        event_type = str(event.get("type") or "")
        if event_type == "output":
            emit_agent_event(
                "tool_progress",
                {"call_id": call_id, "line": str(event.get("line") or "")},
            )
        elif event_type == "final":
            final_result = event.get("result") if isinstance(event.get("result"), dict) else {}
        elif event_type == "error":
            final_result = {
                "error": str(event.get("error") or "Terminal execution failed."),
                "stdout": "",
                "stderr": str(event.get("error") or "Terminal execution failed."),
                "exit_code": 1,
            }

    response = final_result or {
        "error": "Terminal command did not return a result.",
        "stdout": "",
        "stderr": "Missing terminal result",
        "exit_code": 1,
    }
    status = "success" if int(response.get("exit_code") or 1) == 0 else "error"
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": response, "status": status, "duration_ms": 1},
    )
    return response
