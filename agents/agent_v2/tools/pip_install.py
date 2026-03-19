"""Package install tool with explicit deny-by-default behavior in runtime service."""

from __future__ import annotations

from typing import Any

from ..events import emit_agent_event
from . import new_tool_call_id


def _normalize_packages(packages: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for pkg in packages:
        token = str(pkg or "").strip()
        key = token.lower()
        if not token or key in seen:
            continue
        seen.add(key)
        normalized.append(token)
    return normalized


async def pip_install(
    *,
    user_id: str,
    workspace_id: str,
    data_path: str | None,
    packages: list[str],
) -> dict[str, Any]:
    _ = user_id, workspace_id, data_path
    call_id = new_tool_call_id("pip_install")
    requested = _normalize_packages(packages)
    emit_agent_event(
        "tool_call",
        {
            "tool": "pip_install",
            "args": {"packages": requested},
            "call_id": call_id,
        },
    )

    if not requested:
        payload = {"installed": [], "denied": [], "message": "No package names provided."}
        emit_agent_event(
            "tool_result",
            {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
        )
        return payload

    payload = {
        "installed": [],
        "denied": requested,
        "message": "Runtime package installation is disabled for safety. Install dependencies manually and retry.",
    }
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": payload, "status": "error", "duration_ms": 1},
    )
    return payload
