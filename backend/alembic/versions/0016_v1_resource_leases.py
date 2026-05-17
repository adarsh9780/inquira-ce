"""add durable resource leases

Revision ID: 0016_v1_resource_leases
Revises: 0015_v1_turn_storage_metadata
Create Date: 2026-05-18
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "0016_v1_resource_leases"
down_revision = "0015_v1_turn_storage_metadata"
branch_labels = None
depends_on = None


def _db_role() -> str:
    cfg_role = str(context.config.attributes.get("inquira_db_role") or "").strip().lower()
    if cfg_role in {"auth", "appdata"}:
        return cfg_role
    x_args = context.get_x_argument(as_dictionary=True)
    x_role = str(x_args.get("db", "")).strip().lower()
    if x_role in {"auth", "appdata"}:
        return x_role
    return "appdata"


def upgrade() -> None:
    if _db_role() == "auth":
        return

    op.create_table(
        "v1_resource_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("lease_kind", sa.String(length=64), nullable=False),
        sa.Column("owner_token", sa.String(length=255), nullable=False),
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resource_key", "lease_kind", name="uq_v1_resource_lease_key_kind"),
    )
    op.create_index("ix_v1_resource_leases_type_key", "v1_resource_leases", ["resource_type", "resource_key"], unique=False)
    op.create_index("ix_v1_resource_leases_kind_expires", "v1_resource_leases", ["lease_kind", "leased_until"], unique=False)


def downgrade() -> None:
    if _db_role() == "auth":
        return

    op.drop_index("ix_v1_resource_leases_kind_expires", table_name="v1_resource_leases")
    op.drop_index("ix_v1_resource_leases_type_key", table_name="v1_resource_leases")
    op.drop_table("v1_resource_leases")
