"""Workspace-scoped LangGraph manager.

Each workspace uses an isolated checkpoint database at:
`.../workspaces/<workspace_id>/agent_memory.db`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from ...agent.graph import build_graph


class WorkspaceLangGraphManager:
    """Lazily create and cache LangGraph instances by workspace id."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._graphs: dict[str, Any] = {}
        self._checkpointers: dict[str, Any] = {}

    async def get_graph(self, workspace_id: str, agent_memory_path: Path):
        """Return compiled graph for workspace, creating it if missing."""
        async with self._lock:
            if workspace_id in self._graphs:
                return self._graphs[workspace_id]

            agent_memory_path.parent.mkdir(parents=True, exist_ok=True)
            checkpointer_cm = AsyncSqliteSaver.from_conn_string(str(agent_memory_path))
            checkpointer = await checkpointer_cm.__aenter__()
            graph = build_graph(checkpointer=checkpointer)

            self._checkpointers[workspace_id] = checkpointer_cm
            self._graphs[workspace_id] = graph
            return graph

    async def close_workspace(self, workspace_id: str) -> None:
        """Close and evict one workspace graph/checkpointer."""
        async with self._lock:
            cm = self._checkpointers.pop(workspace_id, None)
            self._graphs.pop(workspace_id, None)
            if cm is not None:
                await cm.__aexit__(None, None, None)

    async def shutdown(self) -> None:
        """Close all open checkpointers."""
        async with self._lock:
            workspace_ids = list(self._checkpointers.keys())
            for workspace_id in workspace_ids:
                cm = self._checkpointers.pop(workspace_id, None)
                self._graphs.pop(workspace_id, None)
                if cm is not None:
                    await cm.__aexit__(None, None, None)
