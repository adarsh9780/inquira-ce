"""add sibling order for turn tree editing

Revision ID: 0020_v1_turn_sibling_order
Revises: 0019_v1_dataset_schema_status_metadata
Create Date: 2026-05-19 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0020_v1_turn_sibling_order"
down_revision: Union[str, Sequence[str], None] = "0019_v1_dataset_schema_status_metadata"
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

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("sibling_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_index("ix_v1_turns_parent_sibling_order", ["conversation_id", "parent_turn_id", "sibling_order"])

    op.execute("UPDATE v1_turns SET sibling_order = seq_no WHERE sibling_order = 0")


def downgrade() -> None:
    if _db_role() == "auth":
        return

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.drop_index("ix_v1_turns_parent_sibling_order")
        batch_op.drop_column("sibling_order")
