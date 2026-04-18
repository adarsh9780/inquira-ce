"""Conversation memory summarizer helpers for agent v2."""

from __future__ import annotations

from typing import Any


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_stringify_content(item) for item in content if _stringify_content(item))
    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text") or "")
        return str(content)
    return str(content or "")


def _message_role(message: Any) -> str:
    msg_type = str(getattr(message, "type", "") or "").strip().lower()
    if msg_type in {"human", "user"}:
        return "user"
    if msg_type in {"ai", "assistant"}:
        return "assistant"
    if msg_type == "tool":
        return "tool"
    return "other"


def _truncate_line(text: str, *, limit: int = 220) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 3)].rstrip() + "..."


def _summarize_older_messages(
    older_messages: list[Any],
    *,
    max_summary_chars: int = 2000,
) -> str:
    if not older_messages:
        return ""

    user_points: list[str] = []
    assistant_points: list[str] = []
    tool_points: list[str] = []

    for msg in older_messages:
        role = _message_role(msg)
        text = _truncate_line(_stringify_content(getattr(msg, "content", "")), limit=200)
        if not text:
            continue
        if role == "user":
            user_points.append(text)
        elif role == "assistant":
            assistant_points.append(text)
        elif role == "tool":
            tool_points.append(text)

    lines: list[str] = []
    if user_points:
        lines.append("User requests:")
        for point in user_points[-8:]:
            lines.append(f"- {point}")
    if assistant_points:
        lines.append("Assistant progress:")
        for point in assistant_points[-6:]:
            lines.append(f"- {point}")
    if tool_points:
        lines.append("Tool outcomes:")
        for point in tool_points[-6:]:
            lines.append(f"- {point}")

    summary = "\n".join(lines).strip()
    if not summary:
        return ""
    return summary[: max(200, int(max_summary_chars))]


def build_conversation_memory(
    messages: list[Any],
    *,
    max_recent_messages: int = 10,
    max_summary_chars: int = 2000,
) -> dict[str, Any]:
    safe_recent = max(1, int(max_recent_messages))
    if not isinstance(messages, list):
        return {"recent_messages": [], "summary": ""}

    recent_messages = list(messages[-safe_recent:])
    older_messages = list(messages[:-safe_recent]) if len(messages) > safe_recent else []
    summary = _summarize_older_messages(
        older_messages,
        max_summary_chars=max_summary_chars,
    )
    return {
        "recent_messages": recent_messages,
        "summary": summary,
    }


def summarize_messages(messages: list[Any], *, max_messages: int = 10) -> list[Any]:
    """Return bounded recent messages while memory summary is handled separately."""
    memory = build_conversation_memory(messages, max_recent_messages=max_messages)
    recent_messages = memory.get("recent_messages")
    return list(recent_messages) if isinstance(recent_messages, list) else []
