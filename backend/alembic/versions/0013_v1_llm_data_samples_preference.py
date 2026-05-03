"""Add LLM data samples privacy preference.

Revision ID: 0013_v1_llm_data_samples_preference
Revises: 0012_v1_turn_tree_metadata
Create Date: 2026-05-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_v1_llm_data_samples_preference"
down_revision = "0012_v1_turn_tree_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "v1_user_preferences",
        sa.Column("allow_llm_data_samples", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("v1_user_preferences", "allow_llm_data_samples")
