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


def _normalize_alembic_url(database_url: str) -> str:
    """Convert async runtime URL into sync URL for Alembic/introspection."""
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


def _upgrade_or_stamp_schema(*, alembic_ini: Path, db_role: str, database_url: str, expected_table: str) -> None:
    cfg = Config(str(alembic_ini))
    normalized_url = _normalize_alembic_url(database_url)
    cfg.set_main_option("sqlalchemy.url", normalized_url)
    cfg.attributes["inquira_db_role"] = db_role

    try:
        command.upgrade(cfg, "head")
        return
    except Exception as exc:  # noqa: BLE001
        message = str(exc).lower()
        if "already exists" not in message:
            raise

    sync_engine = create_engine(normalized_url)
    try:
        inspector = inspect(sync_engine)
        tables = set(inspector.get_table_names())
        has_expected_schema = expected_table in tables
        has_alembic_version = "alembic_version" in tables
    finally:
        sync_engine.dispose()

    if has_expected_schema and not has_alembic_version:
        command.stamp(cfg, "head")
        return

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
