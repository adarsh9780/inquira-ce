"""add dedicated coding model preference field

Revision ID: 0005_v1_coding_model_preference
Revises: 0004_v1_llm_provider_preferences
Create Date: 2026-03-18 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0005_v1_coding_model_preference"
down_revision: Union[str, Sequence[str], None] = "0004_v1_llm_provider_preferences"
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
        sa.Column(
            "selected_coding_model",
            sa.String(length=120),
            nullable=False,
            server_default="google/gemini-2.5-flash",
        ),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "selected_coding_model")
