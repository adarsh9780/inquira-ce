"""Conversation and turn ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Conversation(Base):
    """Conversation container within a workspace."""

    __tablename__ = "v1_conversations"
    __table_args__ = (Index("ix_v1_conversations_workspace_updated", "workspace_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("v1_workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("v1_users.id", ondelete="CASCADE"), index=True, nullable=False)
    last_turn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="conversations")
    turns = relationship("Turn", back_populates="conversation", cascade="all, delete-orphan")


class Turn(Base):
    """One user+assistant turn in a conversation."""

    __tablename__ = "v1_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq_no", name="uq_v1_turn_seq"),
        Index("ix_v1_turns_conversation_created", "conversation_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("v1_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    user_text: Mapped[str] = mapped_column(String, nullable=False)
    assistant_text: Mapped[str] = mapped_column(String, nullable=False)
    tool_events_json: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String, nullable=True)
    code_snapshot: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="turns")
