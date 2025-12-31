"""
Centralized path utilities for Inquira.
=====================================

SINGLE SOURCE OF TRUTH for all path constants and path generation.

This module provides:
- Base directory constants
- File naming conventions
- User directory management
- DuckDB database paths
- Per-dataset subfolder management (schema + cache)

USAGE:
    from inquira.core.path_utils import (
        BASE_DIR, CATALOG_DB_NAME,
        get_user_dir, get_database_path, get_schema_path, get_preview_cache_path
    )
"""

from pathlib import Path
from typing import Optional
from functools import lru_cache

# =============================================================================
# CONSTANTS - Change these in ONE place to affect the entire application
# =============================================================================

# Base directory for all Inquira data
BASE_DIR = Path.home() / ".inquira"

# Main SQLite catalog database filename
CATALOG_DB_NAME = "inquira.db"
CATALOG_DB_PATH = BASE_DIR / CATALOG_DB_NAME

# DuckDB file suffix pattern (username-based)
DUCKDB_SUFFIX = "_data.duckdb"

# Schema and cache filenames within dataset folders
SCHEMA_FILENAME = "schema.json"
PREVIEW_CACHE_PREFIX = "preview_"
PREVIEW_CACHE_EXT = ".pkl"

# Sample types for preview caching
SAMPLE_TYPE_RANDOM = "random"
SAMPLE_TYPE_FIRST = "first"


# =============================================================================
# USERNAME LOOKUP (Cached for performance)
# =============================================================================

@lru_cache(maxsize=128)
def get_username_for_user(user_id: str) -> str:
    """Get username for a user_id, with caching.
    
    Raises:
        ValueError: If no username found for the user_id
    """
    from ..database.database import get_username_by_user_id
    username = get_username_by_user_id(user_id)
    if not username:
        raise ValueError(f"No username found for user_id: {user_id}")
    return username


def clear_username_cache():
    """Clear the username cache (useful for testing or after user updates)."""
    get_username_for_user.cache_clear()


# =============================================================================
# PATH GENERATION FUNCTIONS
# =============================================================================

def get_user_dir(user_id: str, create: bool = True) -> Path:
    """Get the base directory for a user (by username).
    
    Args:
        user_id: The user's UUID
        create: Whether to create the directory if it doesn't exist
    
    Returns:
        Path to ~/.inquira/{username}/
    """
    username = get_username_for_user(user_id)
    user_dir = BASE_DIR / username
    if create:
        user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_inquira_home() -> Path:
    """Get the base directory for all Inquira data (~/.inquira)."""
    return BASE_DIR


def get_database_path(user_id: str) -> Path:
    """Get the DuckDB database path for a user.
    
    Returns:
        Path to ~/.inquira/{username}/{username}_data.duckdb
    """
    username = get_username_for_user(user_id)
    return get_user_dir(user_id) / f"{username}{DUCKDB_SUFFIX}"


def get_dataset_dir(user_id: str, table_name: str, create: bool = True) -> Path:
    """Get the directory for a specific dataset.
    
    Args:
        user_id: The user's UUID
        table_name: The DuckDB table name for this dataset
        create: Whether to create the directory if it doesn't exist
    
    Returns:
        Path to ~/.inquira/{username}/{table_name}/
    """
    dataset_dir = get_user_dir(user_id) / table_name
    if create:
        dataset_dir.mkdir(parents=True, exist_ok=True)
    return dataset_dir


def get_schema_path(user_id: str, table_name: str) -> Path:
    """Get the schema.json path for a dataset.
    
    Returns:
        Path to ~/.inquira/{username}/{table_name}/schema.json
    """
    return get_dataset_dir(user_id, table_name) / SCHEMA_FILENAME


def get_preview_cache_path(user_id: str, table_name: str, sample_type: str) -> Path:
    """Get the preview cache path for a dataset.
    
    Args:
        sample_type: One of SAMPLE_TYPE_RANDOM or SAMPLE_TYPE_FIRST
    
    Returns:
        Path to ~/.inquira/{username}/{table_name}/preview_{sample_type}.pkl
    """
    filename = f"{PREVIEW_CACHE_PREFIX}{sample_type}{PREVIEW_CACHE_EXT}"
    return get_dataset_dir(user_id, table_name) / filename


# =============================================================================
# LEGACY PATH FUNCTIONS (for migration compatibility)
# =============================================================================

def get_legacy_user_dir(user_id: str) -> Path:
    """Get the OLD user directory path (UUID-based, for migration).
    
    Returns:
        Path to ~/.inquira/{user_id}/ (old structure)
    """
    return BASE_DIR / user_id


def get_legacy_duckdb_path(user_id: str) -> Path:
    """Get the OLD DuckDB path (UUID-based, for migration).
    
    Returns:
        Path to ~/.inquira/{user_id}/{user_id}_data.duckdb (old structure)
    """
    return get_legacy_user_dir(user_id) / f"{user_id}{DUCKDB_SUFFIX}"


def get_legacy_schemas_dir(user_id: str) -> Path:
    """Get the OLD schemas directory (flat structure, for migration).
    
    Returns:
        Path to ~/.inquira/{user_id}/schemas/ (old structure)
    """
    return get_legacy_user_dir(user_id) / "schemas"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def list_dataset_dirs(user_id: str) -> list[Path]:
    """List all dataset directories for a user."""
    user_dir = get_user_dir(user_id, create=False)
    if not user_dir.exists():
        return []
    # Exclude the DuckDB file and any non-directories
    return [d for d in user_dir.iterdir() if d.is_dir()]


def ensure_base_dir() -> Path:
    """Ensure the base Inquira directory exists."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    return BASE_DIR


def user_needs_migration(user_id: str) -> bool:
    """Check if a user's folder needs migration from UUID to username structure.
    
    Returns True if:
    - Legacy UUID folder exists AND
    - New username folder does not exist (or is the same)
    """
    legacy_dir = get_legacy_user_dir(user_id)
    if not legacy_dir.exists():
        return False
    
    try:
        username = get_username_for_user(user_id)
        new_dir = BASE_DIR / username
        # If legacy dir and new dir are the same path, no migration needed
        # This happens when user_id == username (unlikely but possible)
        return legacy_dir != new_dir and not new_dir.exists()
    except ValueError:
        # No username found - can't migrate
        return False
