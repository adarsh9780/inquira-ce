"""Shared database access registry and coordination primitives."""

from .registry import (
    AccessMode,
    DatabaseRole,
    DatabaseSpec,
    OwnershipMode,
    can_accessor_use_database,
    get_database_spec,
    list_database_specs,
)
from .scratchpad_db import ScratchpadOfflineAdapter, ScratchpadRuntimeAdapter
from .workspace_db import WorkspaceOfflineAdapter, WorkspaceRuntimeAdapter

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
