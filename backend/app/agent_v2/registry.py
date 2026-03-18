"""Agent v2 runtime bindings."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable


@dataclass(frozen=True)
class AgentBindings:
    version: str
    build_graph: Callable[..., Any]
    build_input_state: Callable[..., Any]
    set_stream_token_emitter: Callable[[Callable[[str, str], None] | None], Any] | None
    reset_stream_token_emitter: Callable[[Any], None] | None


@lru_cache(maxsize=1)
def get_agent_bindings() -> AgentBindings:
    from .graph import build_graph
    from .state import build_input_state
    from .streaming import reset_stream_token_emitter, set_stream_token_emitter

    return AgentBindings(
        version="agent_v2",
        build_graph=build_graph,
        build_input_state=build_input_state,
        set_stream_token_emitter=set_stream_token_emitter,
        reset_stream_token_emitter=reset_stream_token_emitter,
    )
