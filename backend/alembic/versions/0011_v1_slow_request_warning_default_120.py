"""set slow request warning default to 120 seconds

Revision ID: 0011_v1_slow_request_warning_default_120
Revises: 0010_v1_slow_request_warning_preference
Create Date: 2026-04-19 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0011_v1_slow_request_warning_default_120"
down_revision: Union[str, Sequence[str], None] = "0010_v1_slow_request_warning_preference"
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
    bind = op.get_bind()
    dialect_name = str(getattr(getattr(bind, "dialect", None), "name", "")).strip().lower()
    if dialect_name == "sqlite":
        # SQLite does not support ALTER COLUMN SET DEFAULT directly.
        with op.batch_alter_table("v1_user_preferences", recreate="auto") as batch_op:
            batch_op.alter_column(
                "slow_request_warning_seconds",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("120"),
            )
    else:
        op.alter_column(
            "v1_user_preferences",
            "slow_request_warning_seconds",
            server_default="120",
        )
    op.execute(
        sa.text(
            "UPDATE v1_user_preferences "
            "SET slow_request_warning_seconds = 120 "
            "WHERE slow_request_warning_seconds = 30"
        )
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    bind = op.get_bind()
    dialect_name = str(getattr(getattr(bind, "dialect", None), "name", "")).strip().lower()
    if dialect_name == "sqlite":
        with op.batch_alter_table("v1_user_preferences", recreate="auto") as batch_op:
            batch_op.alter_column(
                "slow_request_warning_seconds",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("30"),
            )
    else:
        op.alter_column(
            "v1_user_preferences",
            "slow_request_warning_seconds",
            server_default="30",
        )
    op.execute(
        sa.text(
            "UPDATE v1_user_preferences "
            "SET slow_request_warning_seconds = 30 "
            "WHERE slow_request_warning_seconds = 120"
        )
    )
