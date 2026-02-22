"""User and session ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import UserPlan


class User(Base):
    """Application user account."""

    __tablename__ = "v1_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    plan: Mapped[UserPlan] = mapped_column(Enum(UserPlan), default=UserPlan.FREE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", cascade="all, delete-orphan", uselist=False)


class UserSession(Base):
    """Cookie-backed user session record."""

    __tablename__ = "v1_user_sessions"

    session_token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("v1_users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="sessions")
