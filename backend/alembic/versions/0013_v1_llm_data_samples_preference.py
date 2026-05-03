"""Add LLM data samples privacy preference.

Revision ID: 0013_v1_llm_data_samples_preference
Revises: 0012_v1_turn_tree_metadata
Create Date: 2026-05-03
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "0013_v1_llm_data_samples_preference"
down_revision = "0012_v1_turn_tree_metadata"
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
    op.add_column(
        "v1_user_preferences",
        sa.Column("allow_llm_data_samples", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "allow_llm_data_samples")
