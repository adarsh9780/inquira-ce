"""Shared SQLAlchemy declarative base for API v1 models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class inherited by all ORM models."""

    pass
