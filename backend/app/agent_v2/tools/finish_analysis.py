"""Finalization helper tool for agent v2."""

from __future__ import annotations

from ..events import emit_agent_event
from . import new_tool_call_id


def finish_analysis(*, explanation: str, code: str | None = None) -> dict[str, str]:
    call_id = new_tool_call_id("finish_analysis")
    emit_agent_event(
        "tool_call",
        {"tool": "finish_analysis", "args": {}, "call_id": call_id},
    )
    payload = {
        "final_explanation": str(explanation or "").strip(),
        "final_code": str(code or "").strip(),
    }
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": payload, "status": "success", "duration_ms": 1},
    )
    return payload
