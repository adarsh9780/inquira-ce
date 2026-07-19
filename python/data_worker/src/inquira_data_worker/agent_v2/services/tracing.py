"""Optional tracing hooks for the embedded desktop worker.

The standalone application deliberately has no telemetry dependency. These
functions preserve the agent graph contract while keeping execution local.
"""

from __future__ import annotations

def init_phoenix_tracing() -> bool:
    return False


def reset_phoenix_tracing_state() -> None:
    return None
