"""SQLAlchemy declarative bases for split API v1 databases."""

from sqlalchemy.orm import DeclarativeBase


class AuthBase(DeclarativeBase):
    """Base class for auth/session models stored in auth DB."""

    pass


class AppDataBase(DeclarativeBase):
    """Base class for product/workspace/chat models stored in appdata DB."""

    pass


# Backwards alias retained for appdata-side imports.
Base = AppDataBase
