"""Filesystem operations for workspace-scoped storage.

All file operations are async-compatible by pushing sync filesystem work
into worker threads.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
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
    def build_manifest_path(username: str, workspace_id: str) -> Path:
        """Return workspace manifest path."""
        return WorkspaceStorageService.build_workspace_dir(username, workspace_id) / "workspace.json"

    @staticmethod
    async def ensure_workspace_dirs(username: str, workspace_id: str) -> Path:
        """Create workspace directories and return workspace root path."""
        workspace_dir = WorkspaceStorageService.build_workspace_dir(username, workspace_id)

        def _create() -> None:
            workspace_dir.mkdir(parents=True, exist_ok=True)
            (workspace_dir / "context").mkdir(parents=True, exist_ok=True)
            (workspace_dir / "meta").mkdir(parents=True, exist_ok=True)
            pyproject_path = workspace_dir / "pyproject.toml"
            if not pyproject_path.exists():
                safe_name = "".join(ch if (ch.isalnum() or ch in {"-", "_"}) else "-" for ch in workspace_id).strip("-")
                if not safe_name:
                    safe_name = "workspace-project"
                pyproject_path.write_text(
                    (
                        "[project]\n"
                        f'name = "{safe_name}"\n'
                        'version = "0.1.0"\n'
                        'description = "Workspace-scoped runtime project metadata"\n'
                        'requires-python = ">=3.12"\n'
                        "dependencies = []\n"
                    ),
                    encoding="utf-8",
                )

        await asyncio.to_thread(_create)
        return workspace_dir

    @staticmethod
    async def write_workspace_manifest(
        username: str,
        workspace_id: str,
        workspace_name: str,
        normalized_name: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> Path:
        """Persist workspace metadata manifest in workspace root."""
        manifest_path = WorkspaceStorageService.build_manifest_path(username, workspace_id)
        workspace_dir = manifest_path.parent

        payload = {
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "normalized_name": normalized_name,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }

        def _write() -> None:
            workspace_dir.mkdir(parents=True, exist_ok=True)
            with manifest_path.open("w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)

        await asyncio.to_thread(_write)
        return manifest_path

    @staticmethod
    async def hard_delete_workspace(username: str, workspace_id: str) -> None:
        """Delete the workspace directory recursively."""
        workspace_dir = WorkspaceStorageService.build_workspace_dir(username, workspace_id)

        def _delete() -> None:
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)

        await asyncio.to_thread(_delete)
