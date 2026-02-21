"""Filesystem operations for workspace-scoped storage.

All file operations are async-compatible by pushing sync filesystem work
into worker threads.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path


class WorkspaceStorageService:
    """Create and delete workspace directory trees."""

    @staticmethod
    def _user_root(username: str) -> Path:
        return Path.home() / ".inquira" / username / "workspaces"

    @staticmethod
    def build_workspace_dir(username: str, workspace_id: str) -> Path:
        """Return workspace root path."""
        return WorkspaceStorageService._user_root(username) / workspace_id

    @staticmethod
    def build_duckdb_path(username: str, workspace_id: str) -> Path:
        """Return workspace DuckDB path."""
        return WorkspaceStorageService.build_workspace_dir(username, workspace_id) / "workspace.duckdb"

    @staticmethod
    def build_agent_memory_path(username: str, workspace_id: str) -> Path:
        """Return workspace LangGraph memory DB path."""
        return WorkspaceStorageService.build_workspace_dir(username, workspace_id) / "agent_memory.db"

    @staticmethod
    async def ensure_workspace_dirs(username: str, workspace_id: str) -> Path:
        """Create workspace directories and return workspace root path."""
        workspace_dir = WorkspaceStorageService.build_workspace_dir(username, workspace_id)

        def _create() -> None:
            workspace_dir.mkdir(parents=True, exist_ok=True)
            (workspace_dir / "context").mkdir(parents=True, exist_ok=True)
            (workspace_dir / "meta").mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(_create)
        return workspace_dir

    @staticmethod
    async def hard_delete_workspace(username: str, workspace_id: str) -> None:
        """Delete the workspace directory recursively."""
        workspace_dir = WorkspaceStorageService.build_workspace_dir(username, workspace_id)

        def _delete() -> None:
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)

        await asyncio.to_thread(_delete)
