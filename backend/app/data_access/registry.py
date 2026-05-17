"""Canonical registry for backend storage systems and access policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DatabaseRole(StrEnum):
    """Business role for a backend-owned storage system."""

    CONTROL_PLANE = "control_plane"
    WORKSPACE_DATA = "workspace_data"
    ARTIFACT_SCRATCHPAD = "artifact_scratchpad"
    ARTIFACT_BLOB = "artifact_blob"


class OwnershipMode(StrEnum):
    """Who owns live read/write access for a database."""

    REQUEST_SESSION = "request_session"
    KERNEL_OWNED = "kernel_owned"
    OFFLINE_MAINTENANCE = "offline_maintenance"


class AccessMode(StrEnum):
    """Normalized access intents used by the access-policy layer."""

    READ_LIVE = "read_live"
    WRITE_LIVE = "write_live"
    READ_OFFLINE = "read_offline"
    WRITE_OFFLINE = "write_offline"
    METADATA = "metadata"


@dataclass(frozen=True)
class DatabaseSpec:
    """Registry entry describing one backend storage system."""

    db_id: str
    role: DatabaseRole
    ownership_mode: OwnershipMode
    path_builder: str
    migration_strategy: str
    healthcheck: str
    allowed_accessors: tuple[str, ...]


_DATABASE_SPECS: dict[str, DatabaseSpec] = {
    "auth_sqlite": DatabaseSpec(
        db_id="auth_sqlite",
        role=DatabaseRole.CONTROL_PLANE,
        ownership_mode=OwnershipMode.REQUEST_SESSION,
        path_builder="settings.auth_db_url",
        migration_strategy="alembic:auth",
        healthcheck="sqlalchemy-select-1",
        allowed_accessors=("sqlalchemy_session", "repository", "maintenance_task"),
    ),
    "appdata_sqlite": DatabaseSpec(
        db_id="appdata_sqlite",
        role=DatabaseRole.CONTROL_PLANE,
        ownership_mode=OwnershipMode.REQUEST_SESSION,
        path_builder="settings.appdata_db_url",
        migration_strategy="alembic:appdata",
        healthcheck="sqlalchemy-select-1",
        allowed_accessors=("sqlalchemy_session", "repository", "background_worker"),
    ),
    "workspace_duckdb": DatabaseSpec(
        db_id="workspace_duckdb",
        role=DatabaseRole.WORKSPACE_DATA,
        ownership_mode=OwnershipMode.KERNEL_OWNED,
        path_builder="WorkspaceStorageService.build_duckdb_path",
        migration_strategy="filesystem-bootstrap",
        healthcheck="kernel-describe-main",
        allowed_accessors=("workspace_runtime_adapter", "workspace_offline_adapter"),
    ),
    "scratchpad_duckdb": DatabaseSpec(
        db_id="scratchpad_duckdb",
        role=DatabaseRole.ARTIFACT_SCRATCHPAD,
        ownership_mode=OwnershipMode.KERNEL_OWNED,
        path_builder="WorkspaceStorageService.build_scratchpad_db_path",
        migration_strategy="scratchpad-bootstrap",
        healthcheck="kernel-artifact-manifest-count",
        allowed_accessors=("scratchpad_runtime_adapter", "scratchpad_offline_adapter"),
    ),
    "turn_blob_store": DatabaseSpec(
        db_id="turn_blob_store",
        role=DatabaseRole.ARTIFACT_BLOB,
        ownership_mode=OwnershipMode.OFFLINE_MAINTENANCE,
        path_builder="TurnBundleService.build_conversation_dir",
        migration_strategy="filesystem-manifest-migration",
        healthcheck="path-exists",
        allowed_accessors=("turn_bundle_service", "artifact_blob_store", "storage_cleanup"),
    ),
}

_ACCESS_POLICY: dict[OwnershipMode, frozenset[AccessMode]] = {
    OwnershipMode.REQUEST_SESSION: frozenset(
        {
            AccessMode.READ_LIVE,
            AccessMode.WRITE_LIVE,
            AccessMode.READ_OFFLINE,
            AccessMode.WRITE_OFFLINE,
            AccessMode.METADATA,
        }
    ),
    OwnershipMode.KERNEL_OWNED: frozenset(
        {
            AccessMode.READ_LIVE,
            AccessMode.WRITE_LIVE,
            AccessMode.METADATA,
        }
    ),
    OwnershipMode.OFFLINE_MAINTENANCE: frozenset(
        {
            AccessMode.READ_OFFLINE,
            AccessMode.WRITE_OFFLINE,
            AccessMode.METADATA,
        }
    ),
}


def get_database_spec(db_id: str) -> DatabaseSpec:
    """Return the registered database spec or raise for unknown ids."""
    try:
        return _DATABASE_SPECS[db_id]
    except KeyError as exc:
        raise KeyError(f"Unknown database spec: {db_id}") from exc


def list_database_specs() -> tuple[DatabaseSpec, ...]:
    """Return all registered database specs in stable order."""
    return tuple(_DATABASE_SPECS.values())


def can_accessor_use_database(
    *,
    accessor: str,
    db_id: str,
    access_mode: AccessMode,
) -> bool:
    """Return True when the accessor is allowed to use the database in the given mode."""
    spec = get_database_spec(db_id)
    if accessor not in spec.allowed_accessors:
        return False
    if access_mode not in _ACCESS_POLICY[spec.ownership_mode]:
        return False
    if accessor.endswith("_runtime_adapter") and access_mode in {
        AccessMode.READ_OFFLINE,
        AccessMode.WRITE_OFFLINE,
    }:
        return False
    if accessor.endswith("_offline_adapter") and access_mode in {
        AccessMode.READ_LIVE,
        AccessMode.WRITE_LIVE,
    }:
        return False
    return True
