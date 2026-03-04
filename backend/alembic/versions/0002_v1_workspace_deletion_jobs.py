"""add v1 workspace deletion jobs table

Revision ID: 0002_v1_workspace_deletion_jobs
Revises: 0001_v1_initial_schema
Create Date: 2026-02-21 00:30:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0002_v1_workspace_deletion_jobs"
down_revision: Union[str, Sequence[str], None] = "0001_v1_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
        "v1_workspace_deletion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_principal_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_principal_id"], ["v1_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_v1_workspace_deletion_jobs_owner_principal_id",
        "v1_workspace_deletion_jobs",
        ["owner_principal_id"],
        unique=False,
    )
    op.create_index(
        "ix_v1_ws_delete_jobs_owner_created",
        "v1_workspace_deletion_jobs",
        ["owner_principal_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_v1_ws_delete_jobs_workspace_status",
        "v1_workspace_deletion_jobs",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_index("ix_v1_ws_delete_jobs_workspace_status", table_name="v1_workspace_deletion_jobs")
    op.drop_index("ix_v1_ws_delete_jobs_owner_created", table_name="v1_workspace_deletion_jobs")
    op.drop_index("ix_v1_workspace_deletion_jobs_owner_principal_id", table_name="v1_workspace_deletion_jobs")
    op.drop_table("v1_workspace_deletion_jobs")
