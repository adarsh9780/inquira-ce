"""Tool helpers for agent v2."""

from __future__ import annotations

import uuid


def new_tool_call_id(tool_name: str) -> str:
    prefix = "".join(ch for ch in str(tool_name or "tool") if ch.isalnum())[:20] or "tool"
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
