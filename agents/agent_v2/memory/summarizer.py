"""Conversation memory summarizer placeholder for agent v2."""

from __future__ import annotations

from typing import Any


def summarize_messages(messages: list[Any], *, max_messages: int = 10) -> list[Any]:
    """Return a bounded recent window until full summarization is introduced."""
    safe_limit = max(1, int(max_messages))
    return list(messages[-safe_limit:])
