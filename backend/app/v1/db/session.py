"""Async database engine/session utilities for split API v1 databases."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.settings import settings


SQLITE_BUSY_TIMEOUT_MS = 30_000


def _is_sqlite_url(database_url: str) -> bool:
    return str(database_url or "").startswith(("sqlite://", "sqlite+aiosqlite://"))


def _sqlite_connect_args(database_url: str) -> dict[str, object]:
    if not _is_sqlite_url(database_url):
        return {}
    return {"timeout": SQLITE_BUSY_TIMEOUT_MS / 1000}


def _configure_sqlite_pragmas(engine: AsyncEngine, database_url: str) -> None:
    if not _is_sqlite_url(database_url):
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


def _create_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=_sqlite_connect_args(database_url),
    )
    _configure_sqlite_pragmas(engine, database_url)
    return engine


auth_engine: AsyncEngine = _create_engine(settings.auth_db_url)

appdata_engine: AsyncEngine = _create_engine(settings.appdata_db_url)

AuthSessionLocal = async_sessionmaker(
    bind=auth_engine,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
    expire_on_commit=False,
)

AppDataSessionLocal = async_sessionmaker(
    bind=appdata_engine,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_auth_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session for request-scoped auth DB access."""
    async with AuthSessionLocal() as session:
        yield session


async def get_appdata_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session for request-scoped appdata DB access."""
    async with AppDataSessionLocal() as session:
        yield session
