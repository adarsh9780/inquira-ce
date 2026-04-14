"""add llm advanced generation settings to preferences

Revision ID: 0008_v1_llm_advanced_settings
Revises: 0007_v1_provider_model_catalog_overrides
Create Date: 2026-04-14 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0008_v1_llm_advanced_settings"
down_revision: Union[str, Sequence[str], None] = "0007_v1_provider_model_catalog_overrides"
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
    op.add_column(
        "v1_user_preferences",
        sa.Column("llm_temperature", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column("llm_max_tokens", sa.Integer(), nullable=False, server_default="2048"),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column("llm_top_p", sa.Float(), nullable=False, server_default="1"),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column("llm_frequency_penalty", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column("llm_presence_penalty", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "llm_presence_penalty")
    op.drop_column("v1_user_preferences", "llm_frequency_penalty")
    op.drop_column("v1_user_preferences", "llm_top_p")
    op.drop_column("v1_user_preferences", "llm_max_tokens")
    op.drop_column("v1_user_preferences", "llm_temperature")
