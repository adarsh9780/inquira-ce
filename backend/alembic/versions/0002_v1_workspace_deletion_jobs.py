"""add v1 workspace deletion jobs table

Revision ID: 0002_v1_workspace_deletion_jobs
Revises: 0001_v1_initial_schema
Create Date: 2026-02-21 00:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_v1_workspace_deletion_jobs"
down_revision: Union[str, Sequence[str], None] = "0001_v1_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "v1_workspace_deletion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["v1_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_v1_workspace_deletion_jobs_user_id", "v1_workspace_deletion_jobs", ["user_id"], unique=False)
    op.create_index(
        "ix_v1_ws_delete_jobs_user_created",
        "v1_workspace_deletion_jobs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_v1_ws_delete_jobs_workspace_status",
        "v1_workspace_deletion_jobs",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_v1_ws_delete_jobs_workspace_status", table_name="v1_workspace_deletion_jobs")
    op.drop_index("ix_v1_ws_delete_jobs_user_created", table_name="v1_workspace_deletion_jobs")
    op.drop_index("ix_v1_workspace_deletion_jobs_user_id", table_name="v1_workspace_deletion_jobs")
    op.drop_table("v1_workspace_deletion_jobs")
