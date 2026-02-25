"""User preferences ORM model for API v1."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class UserPreferences(Base):
    """Per-user persisted UI/runtime preferences."""

    __tablename__ = "v1_user_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("v1_users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    selected_model: Mapped[str] = mapped_column(
        String(120), nullable=False, default="google/gemini-2.5-flash"
    )
    schema_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    allow_schema_sample_values: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    chat_overlay_width: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    is_sidebar_collapsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    hide_shortcuts_modal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active_workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active_dataset_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    active_table_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="preferences")
