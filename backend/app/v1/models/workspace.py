"""Workspace and dataset ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class Workspace(Base):
    """User workspace containing one DuckDB database and related assets."""

    __tablename__ = "v1_workspaces"
    __table_args__ = (
        UniqueConstraint("user_id", "name_normalized", name="uq_v1_workspace_user_name_norm"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("v1_users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duckdb_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="workspaces")
    datasets = relationship("WorkspaceDataset", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceDataset(Base):
    """Catalog entry for a dataset imported into a workspace DuckDB."""

    __tablename__ = "v1_workspace_datasets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_fingerprint", name="uq_v1_ws_fingerprint"),
        UniqueConstraint("workspace_id", "table_name", name="uq_v1_ws_table_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("v1_workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_mtime: Mapped[float | None] = mapped_column(nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="datasets")
