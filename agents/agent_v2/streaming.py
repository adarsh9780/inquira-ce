"""Token streaming helpers for agent v2."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Callable


_STREAM_TOKEN_EMITTER: ContextVar[Callable[[str, str], None] | None] = ContextVar(
    "_agent_v2_stream_token_emitter",
    default=None,
)


def set_stream_token_emitter(emitter: Callable[[str, str], None] | None):
    return _STREAM_TOKEN_EMITTER.set(emitter)


def reset_stream_token_emitter(token) -> None:
    _STREAM_TOKEN_EMITTER.reset(token)


def emit_stream_token(node_name: str, text: str) -> None:
    emitter = _STREAM_TOKEN_EMITTER.get()
    if not callable(emitter):
        return
    chunk = str(text or "")
    if not chunk:
        return
    emitter(str(node_name or ""), chunk)
