"""Durable resource lease ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import AppDataBase


class ResourceLease(AppDataBase):
    """Durable lease row used to coordinate workspace-scoped resources."""

    __tablename__ = "v1_resource_leases"
    __table_args__ = (
        UniqueConstraint("resource_key", "lease_kind", name="uq_v1_resource_lease_key_kind"),
        Index("ix_v1_resource_leases_type_key", "resource_type", "resource_key"),
        Index("ix_v1_resource_leases_kind_expires", "lease_kind", "leased_until"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_key: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    lease_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_token: Mapped[str] = mapped_column(String(255), nullable=False)
    leased_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
