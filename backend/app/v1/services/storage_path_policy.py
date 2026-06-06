"""Path ownership checks for workspace-managed filesystem data."""

from __future__ import annotations

from pathlib import Path


class StoragePathViolationError(ValueError):
    """Raised when a persisted path escapes its owning storage root."""


def resolve_owned_path(path: str | Path, *, root: str | Path, label: str = "path") -> Path:
    """Resolve a path and require it to remain inside the supplied root."""
    resolved_root = Path(root).expanduser().resolve(strict=False)
    resolved_path = Path(path).expanduser().resolve(strict=False)
    if resolved_path == resolved_root or resolved_root in resolved_path.parents:
        return resolved_path
    raise StoragePathViolationError(f"{label} must remain inside its owned workspace directory.")


def workspace_root_from_duckdb_path(workspace_duckdb_path: str | Path) -> Path:
    """Return the owning workspace directory for a managed DuckDB path."""
    return Path(workspace_duckdb_path).expanduser().resolve(strict=False).parent
