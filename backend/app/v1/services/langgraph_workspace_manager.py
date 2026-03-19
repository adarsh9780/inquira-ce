"""Legacy workspace manager shim.

Embedded backend agent graphs were removed in favor of the external
agents service. This shim preserves existing dependency injection
shapes for workspace lifecycle code that still expects a manager object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class WorkspaceLangGraphManager:
    """Compatibility shim for legacy call sites."""

    async def get_graph(self, workspace_id: str, agent_memory_path: Path) -> Any:
        _ = workspace_id, agent_memory_path
        raise RuntimeError(
            "Embedded LangGraph execution is disabled. Use the external agents API service."
        )

    async def close_workspace(self, workspace_id: str) -> None:
        _ = workspace_id
        return

    async def shutdown(self) -> None:
        return
