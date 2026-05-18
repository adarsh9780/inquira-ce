"""Database initialization entrypoints for split v1 ORM schemas."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from ..core.settings import settings
from .. import models  # noqa: F401  # Ensure model metadata is registered
from .base import AppDataBase, AuthBase
from .session import appdata_engine, auth_engine


CORE_TABLES_BY_ROLE = {
    "auth": {"v1_users", "v1_user_sessions"},
    "appdata": {"v1_principals", "v1_workspaces", "v1_conversations", "v1_turns"},
}


def _target_metadata_for_role(db_role: str):
    return AuthBase.metadata if db_role == "auth" else AppDataBase.metadata


def _bootstrap_schema_from_metadata(*, db_role: str, normalized_url: str) -> None:
    """Create the current ORM schema directly for empty/broken local metadata DBs."""
    sync_engine = create_engine(normalized_url)
    try:
        _target_metadata_for_role(db_role).create_all(sync_engine)
    finally:
        sync_engine.dispose()


def _normalize_alembic_url(database_url: str) -> str:
    """Convert async runtime URL into sync URL for Alembic/introspection."""
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


def _upgrade_or_stamp_schema(*, alembic_ini: Path, db_role: str, database_url: str, expected_table: str) -> None:
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    normalized_url = _normalize_alembic_url(database_url)
    cfg.set_main_option("sqlalchemy.url", normalized_url)
    cfg.attributes["inquira_db_role"] = db_role

    upgrade_exc: Exception | None = None
    try:
        command.upgrade(cfg, "head")
        return
    except Exception as exc:  # noqa: BLE001
        upgrade_exc = exc

    sync_engine = create_engine(normalized_url)
    try:
        inspector = inspect(sync_engine)
        tables = set(inspector.get_table_names())
        has_expected_schema = expected_table in tables
        has_alembic_version = "alembic_version" in tables
        missing_core_tables = CORE_TABLES_BY_ROLE.get(db_role, {expected_table}) - tables
    finally:
        sync_engine.dispose()

    if missing_core_tables:
        _bootstrap_schema_from_metadata(db_role=db_role, normalized_url=normalized_url)
        command.stamp(cfg, "head")
        return

    if has_expected_schema and not has_alembic_version:
        command.stamp(cfg, "head")
        return

    if upgrade_exc is not None:
        raise upgrade_exc

    raise RuntimeError(f"Failed to migrate {db_role} schema to Alembic head.")


async def init_v1_database() -> None:
    """Apply Alembic migrations for auth and appdata schemas."""
    alembic_ini = Path(__file__).resolve().parents[3] / "alembic.ini"
    if alembic_ini.exists():
        await asyncio.to_thread(
            _upgrade_or_stamp_schema,
            alembic_ini=alembic_ini,
            db_role="auth",
            database_url=settings.auth_db_url,
            expected_table="v1_users",
        )
        await asyncio.to_thread(
            _upgrade_or_stamp_schema,
            alembic_ini=alembic_ini,
            db_role="appdata",
            database_url=settings.appdata_db_url,
            expected_table="v1_principals",
        )
        return

    if settings.allow_schema_bootstrap:
        async with auth_engine.begin() as conn:
            await conn.run_sync(AuthBase.metadata.create_all)
        async with appdata_engine.begin() as conn:
            await conn.run_sync(AppDataBase.metadata.create_all)
        return

    raise RuntimeError(
        "Alembic configuration not found and schema bootstrap is disabled. "
        "Set INQUIRA_ALLOW_SCHEMA_BOOTSTRAP=1 for local fallback."
    )
