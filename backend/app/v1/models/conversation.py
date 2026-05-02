"""Conversation and turn ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import AppDataBase


class Conversation(AppDataBase):
    """Conversation container within a workspace."""

    __tablename__ = "v1_conversations"
    __table_args__ = (Index("ix_v1_conversations_workspace_updated", "workspace_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("v1_workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_principal_id: Mapped[str] = mapped_column(
        ForeignKey("v1_principals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    final_turn_id: Mapped[str | None] = mapped_column(
        ForeignKey("v1_turns.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    schema_memory_json: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_memory_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_summary_json: Mapped[str | None] = mapped_column(String, nullable=True)
    migration_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_turn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="conversations")
    created_by_principal = relationship("Principal", back_populates="conversations")
    turns = relationship(
        "Turn",
        back_populates="conversation",
        cascade="all, delete-orphan",
        foreign_keys="Turn.conversation_id",
    )
    final_turn = relationship("Turn", foreign_keys=[final_turn_id], post_update=True)


class Turn(AppDataBase):
    """One user+assistant turn in a conversation."""

    __tablename__ = "v1_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq_no", name="uq_v1_turn_seq"),
        Index("ix_v1_turns_conversation_created", "conversation_id", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("v1_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    parent_turn_id: Mapped[str | None] = mapped_column(
        ForeignKey("v1_turns.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    result_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    code_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    manifest_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artifact_summary_json: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_usage_json: Mapped[str | None] = mapped_column(String, nullable=True)
    execution_summary_json: Mapped[str | None] = mapped_column(String, nullable=True)
    user_text: Mapped[str] = mapped_column(String, nullable=False)
    assistant_text: Mapped[str] = mapped_column(String, nullable=False)
    tool_events_json: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(String, nullable=True)
    code_snapshot: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", back_populates="turns", foreign_keys=[conversation_id])
    parent_turn = relationship("Turn", remote_side=[id], foreign_keys=[parent_turn_id])
