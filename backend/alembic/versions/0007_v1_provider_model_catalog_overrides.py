"""add provider model catalog override storage

Revision ID: 0007_v1_provider_model_catalog_overrides
Revises: 0006_v1_terminal_risk_acknowledged
Create Date: 2026-03-20 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0007_v1_provider_model_catalog_overrides"
down_revision: Union[str, Sequence[str], None] = "0006_v1_terminal_risk_acknowledged"
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
            "provider_model_catalogs_json",
            sa.Text(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "provider_model_catalogs_json")
