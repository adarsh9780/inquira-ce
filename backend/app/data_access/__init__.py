"""Shared database access registry and coordination primitives."""

from __future__ import annotations

from .registry import (
    AccessMode,
    DatabaseRole,
    DatabaseSpec,
    OwnershipMode,
    can_accessor_use_database,
    get_database_spec,
    list_database_specs,
)

__all__ = [
    "AccessMode",
    "DatabaseRole",
    "DatabaseSpec",
    "OwnershipMode",
    "ScratchpadOfflineAdapter",
    "ScratchpadRuntimeAdapter",
    "WorkspaceOfflineAdapter",
    "WorkspaceRuntimeAdapter",
    "can_accessor_use_database",
    "get_database_spec",
    "list_database_specs",
]


def __getattr__(name: str):
    if name in {"ScratchpadOfflineAdapter", "ScratchpadRuntimeAdapter"}:
        from .scratchpad_db import ScratchpadOfflineAdapter, ScratchpadRuntimeAdapter

        return {
            "ScratchpadOfflineAdapter": ScratchpadOfflineAdapter,
            "ScratchpadRuntimeAdapter": ScratchpadRuntimeAdapter,
        }[name]
    if name in {"WorkspaceOfflineAdapter", "WorkspaceRuntimeAdapter"}:
        from .workspace_db import WorkspaceOfflineAdapter, WorkspaceRuntimeAdapter

        return {
            "WorkspaceOfflineAdapter": WorkspaceOfflineAdapter,
            "WorkspaceRuntimeAdapter": WorkspaceRuntimeAdapter,
        }[name]
    raise AttributeError(name)
