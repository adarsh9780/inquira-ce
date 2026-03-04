"""add v1 user preferences table

Revision ID: 0003_v1_user_preferences
Revises: 0002_v1_workspace_deletion_jobs
Create Date: 2026-02-22 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0003_v1_user_preferences"
down_revision: Union[str, Sequence[str], None] = "0002_v1_workspace_deletion_jobs"
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
        "v1_user_preferences",
        sa.Column("principal_id", sa.String(length=36), nullable=False),
        sa.Column("selected_model", sa.String(length=120), nullable=False, server_default="google/gemini-2.5-flash"),
        sa.Column("schema_context", sa.Text(), nullable=False, server_default=""),
        sa.Column("allow_schema_sample_values", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("chat_overlay_width", sa.Float(), nullable=False, server_default=sa.text("0.25")),
        sa.Column("is_sidebar_collapsed", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("hide_shortcuts_modal", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("active_workspace_id", sa.String(length=36), nullable=True),
        sa.Column("active_dataset_path", sa.String(length=1024), nullable=True),
        sa.Column("active_table_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["v1_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("principal_id"),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_table("v1_user_preferences")
