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

__all__ = [
    "AccessMode",
    "DatabaseRole",
    "DatabaseSpec",
    "OwnershipMode",
    "can_accessor_use_database",
    "get_database_spec",
    "list_database_specs",
]
