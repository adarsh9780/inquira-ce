"""Workspace, principal, and dataset ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import AppDataBase


class Principal(AppDataBase):
    """App-data identity anchor mirroring authenticated user identity."""

    __tablename__ = "v1_principals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username_cached: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    plan_cached: Mapped[str] = mapped_column(String(32), nullable=False, default="FREE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspaces = relationship("Workspace", back_populates="owner_principal", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="created_by_principal", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="principal", cascade="all, delete-orphan", uselist=False)
    deletion_jobs = relationship("WorkspaceDeletionJob", back_populates="owner_principal", cascade="all, delete-orphan")
    dataset_deletion_jobs = relationship("WorkspaceDatasetDeletionJob", back_populates="owner_principal", cascade="all, delete-orphan")
    dataset_ingestion_jobs = relationship("WorkspaceDatasetIngestionJob", back_populates="owner_principal", cascade="all, delete-orphan")


class Workspace(AppDataBase):
    """User workspace containing one DuckDB database and related assets."""

    __tablename__ = "v1_workspaces"
    __table_args__ = (
        UniqueConstraint("owner_principal_id", "name_normalized", name="uq_v1_workspace_owner_name_norm"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_principal_id: Mapped[str] = mapped_column(
        ForeignKey("v1_principals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duckdb_path: Mapped[str] = mapped_column(String(512), nullable=False)
    schema_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner_principal = relationship("Principal", back_populates="workspaces")
    datasets = relationship("WorkspaceDataset", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceDataset(AppDataBase):
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


class WorkspaceDeletionJob(AppDataBase):
    """Asynchronous workspace deletion job tracker."""

    __tablename__ = "v1_workspace_deletion_jobs"
    __table_args__ = (
        Index("ix_v1_ws_delete_jobs_owner_created", "owner_principal_id", "created_at"),
        Index("ix_v1_ws_delete_jobs_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_principal_id: Mapped[str] = mapped_column(
        ForeignKey("v1_principals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner_principal = relationship("Principal", back_populates="deletion_jobs")


class WorkspaceDatasetDeletionJob(AppDataBase):
    """Asynchronous dataset physical cleanup tracker."""

    __tablename__ = "v1_dataset_deletion_jobs"
    __table_args__ = (
        Index("ix_v1_ds_delete_jobs_owner_created", "owner_principal_id", "created_at"),
        Index("ix_v1_ds_delete_jobs_ws_table_status", "workspace_id", "table_name", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_principal_id: Mapped[str] = mapped_column(
        ForeignKey("v1_principals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    table_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner_principal = relationship("Principal", back_populates="dataset_deletion_jobs")


class WorkspaceDatasetIngestionJob(AppDataBase):
    """Asynchronous batch dataset ingestion tracker."""

    __tablename__ = "v1_dataset_ingestion_jobs"
    __table_args__ = (
        Index("ix_v1_ds_ingest_jobs_owner_created", "owner_principal_id", "created_at"),
        Index("ix_v1_ds_ingest_jobs_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_principal_id: Mapped[str] = mapped_column(
        ForeignKey("v1_principals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    workspace_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner_principal = relationship("Principal", back_populates="dataset_ingestion_jobs")
