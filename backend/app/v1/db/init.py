"""Database initialization entrypoints for v1 ORM schema."""

from __future__ import annotations

from .base import Base
from .session import engine
from .. import models  # noqa: F401  # Ensure model metadata is registered


async def init_v1_database() -> None:
    """Create all v1 ORM tables if they do not exist.

    Alembic remains the preferred migration path in production. This initializer
    keeps local development bootstrapping deterministic.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
