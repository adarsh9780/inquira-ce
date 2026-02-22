"""Database initialization entrypoints for v1 ORM schema."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from .base import Base
from .session import engine
from ..core.settings import settings
from .. import models  # noqa: F401  # Ensure model metadata is registered


def _normalize_alembic_url(database_url: str) -> str:
    """Convert async runtime URL into sync URL for Alembic/introspection."""
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


async def init_v1_database() -> None:
    """Apply Alembic migrations; optional create_all fallback for local bootstrap."""

    alembic_ini = Path(__file__).resolve().parents[3] / "alembic.ini"
    if alembic_ini.exists():
        cfg = Config(str(alembic_ini))

        def _upgrade_or_stamp_bootstrapped_schema() -> None:
            try:
                command.upgrade(cfg, "head")
                return
            except Exception as exc:  # noqa: BLE001
                message = str(exc).lower()
                if "already exists" not in message:
                    raise

            sync_url = _normalize_alembic_url(settings.database_url)
            sync_engine = create_engine(sync_url)
            try:
                inspector = inspect(sync_engine)
                tables = set(inspector.get_table_names())
                has_v1_schema = "v1_users" in tables
                has_alembic_version = "alembic_version" in tables
            finally:
                sync_engine.dispose()

            if has_v1_schema and not has_alembic_version:
                command.stamp(cfg, "head")
                return
            raise RuntimeError("Failed to migrate v1 schema to Alembic head.")

        await asyncio.to_thread(_upgrade_or_stamp_bootstrapped_schema)
        return

    if settings.allow_schema_bootstrap:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    raise RuntimeError(
        "Alembic configuration not found and schema bootstrap is disabled. "
        "Set INQUIRA_ALLOW_SCHEMA_BOOTSTRAP=1 for local fallback."
    )
