"""Restricted workspace bash tool with streamed progress events."""

from __future__ import annotations

import asyncio
import re
import shlex
from pathlib import Path
from typing import Any

from ..events import emit_agent_event
from ..runtime import load_agent_runtime_config
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
    _ = user_id, workspace_id
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
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=workspace_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=max(5, int(timeout)))
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        response = {"error": "Command timed out.", "stdout": "", "stderr": "Timed out", "exit_code": 124}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": response, "status": "error", "duration_ms": 1},
        )
        return response

    stdout = out_b.decode(errors="ignore")
    stderr = err_b.decode(errors="ignore")
    for line in stdout.splitlines():
        emit_agent_event("tool_progress", {"call_id": call_id, "line": line})
    for line in stderr.splitlines():
        emit_agent_event("tool_progress", {"call_id": call_id, "line": line})

    response = {
        "error": "" if proc.returncode == 0 else (stderr.strip() or "Command failed."),
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": int(proc.returncode or 0),
    }
    status = "success" if int(response.get("exit_code") or 1) == 0 else "error"
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": response, "status": status, "duration_ms": 1},
    )
    return response
