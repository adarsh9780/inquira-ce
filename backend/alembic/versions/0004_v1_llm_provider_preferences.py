"""add provider-aware llm preference fields

Revision ID: 0004_v1_llm_provider_preferences
Revises: 0003_v1_user_preferences
Create Date: 2026-03-07 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0004_v1_llm_provider_preferences"
down_revision: Union[str, Sequence[str], None] = "0003_v1_user_preferences"
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
        sa.Column("llm_provider", sa.String(length=32), nullable=False, server_default="openrouter"),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column(
            "selected_lite_model",
            sa.String(length=120),
            nullable=False,
            server_default="google/gemini-2.5-flash-lite",
        ),
    )
    op.add_column(
        "v1_user_preferences",
        sa.Column("enabled_main_models_json", sa.Text(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "enabled_main_models_json")
    op.drop_column("v1_user_preferences", "selected_lite_model")
    op.drop_column("v1_user_preferences", "llm_provider")
