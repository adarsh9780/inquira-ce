"""add terminal risk acknowledgment preference

Revision ID: 0006_v1_terminal_risk_acknowledged
Revises: 0005_v1_coding_model_preference
Create Date: 2026-03-18 00:00:01
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0006_v1_terminal_risk_acknowledged"
down_revision: Union[str, Sequence[str], None] = "0005_v1_coding_model_preference"
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
            "terminal_risk_acknowledged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "terminal_risk_acknowledged")
