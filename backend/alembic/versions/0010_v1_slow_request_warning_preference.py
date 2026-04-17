"""add slow request warning threshold preference

Revision ID: 0010_v1_slow_request_warning_preference
Revises: 0009_v1_dataset_deletion_jobs
Create Date: 2026-04-17 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0010_v1_slow_request_warning_preference"
down_revision: Union[str, Sequence[str], None] = "0009_v1_dataset_deletion_jobs"
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
            "slow_request_warning_seconds",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_user_preferences", "slow_request_warning_seconds")
