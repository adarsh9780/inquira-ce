"""Async database engine/session utilities for split API v1 databases."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..core.settings import settings


auth_engine: AsyncEngine = create_async_engine(
    settings.auth_db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

appdata_engine: AsyncEngine = create_async_engine(
    settings.appdata_db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

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
