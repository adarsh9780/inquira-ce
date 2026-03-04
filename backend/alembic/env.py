"""Alembic environment configuration for split API v1 schemas."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.v1.core.settings import settings
from app.v1.db.base import AppDataBase, AuthBase
from app.v1 import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _normalize_alembic_url(database_url: str) -> str:
    """Map async runtime DB URLs to sync dialect URLs for Alembic engine."""
    if database_url.startswith("sqlite+aiosqlite://"):
        return database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


def _resolve_db_role() -> str:
    role = str(config.attributes.get("inquira_db_role") or "").strip().lower()
    if role in {"auth", "appdata"}:
        return role

    x_args = context.get_x_argument(as_dictionary=True)
    role = str(x_args.get("db", "")).strip().lower()
    if role in {"auth", "appdata"}:
        return role

    role = str(config.get_main_option("inquira_db_role") or "").strip().lower()
    if role in {"auth", "appdata"}:
        return role

    return "appdata"


def _resolve_sqlalchemy_url(db_role: str) -> str:
    configured_url = str(config.get_main_option("sqlalchemy.url") or "").strip()
    if configured_url and "PLACEHOLDER" not in configured_url:
        return _normalize_alembic_url(configured_url)
    if db_role == "auth":
        return _normalize_alembic_url(settings.auth_db_url)
    return _normalize_alembic_url(settings.appdata_db_url)


db_role = _resolve_db_role()
config.set_main_option("sqlalchemy.url", _resolve_sqlalchemy_url(db_role))
target_metadata = AuthBase.metadata if db_role == "auth" else AppDataBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
