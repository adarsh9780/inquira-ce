"""Shared agent event emitter for streaming non-token events to SSE clients."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Callable


_AGENT_EVENT_EMITTER: ContextVar[Callable[[str, dict[str, Any]], None] | None] = ContextVar(
    "_agent_event_emitter",
    default=None,
)


def set_agent_event_emitter(emitter: Callable[[str, dict[str, Any]], None] | None):
    """Register a per-request event emitter callback."""
    return _AGENT_EVENT_EMITTER.set(emitter)


def reset_agent_event_emitter(token) -> None:
    """Restore previous event emitter callback."""
    _AGENT_EVENT_EMITTER.reset(token)


def emit_agent_event(event: str, payload: dict[str, Any] | None = None) -> None:
    """Emit a structured event when a callback is bound."""
    emitter = _AGENT_EVENT_EMITTER.get()
    if not callable(emitter):
        return
    event_name = str(event or "").strip()
    if not event_name:
        return
    emitter(event_name, dict(payload or {}))
