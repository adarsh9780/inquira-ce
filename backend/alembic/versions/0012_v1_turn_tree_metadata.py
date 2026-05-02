"""add turn tree metadata for branching analysis

Revision ID: 0012_v1_turn_tree_metadata
Revises: 0011_v1_slow_request_warning_default_120
Create Date: 2026-05-02 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


revision: str = "0012_v1_turn_tree_metadata"
down_revision: Union[str, Sequence[str], None] = "0011_v1_slow_request_warning_default_120"
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

    with op.batch_alter_table("v1_conversations", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("final_turn_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("schema_memory_json", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("schema_memory_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("branch_summary_json", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("migration_version", sa.Integer(), nullable=True))
        batch_op.create_index("ix_v1_conversations_final_turn_id", ["final_turn_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_v1_conversations_final_turn_id",
            "v1_turns",
            ["final_turn_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("parent_turn_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("result_kind", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("code_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("manifest_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("artifact_summary_json", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("schema_usage_json", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("execution_summary_json", sa.String(), nullable=True))
        batch_op.create_index("ix_v1_turns_parent_turn_id", ["parent_turn_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_v1_turns_parent_turn_id",
            "v1_turns",
            ["parent_turn_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if _db_role() == "auth":
        return

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_v1_turns_parent_turn_id", type_="foreignkey")
        batch_op.drop_index("ix_v1_turns_parent_turn_id")
        batch_op.drop_column("execution_summary_json")
        batch_op.drop_column("schema_usage_json")
        batch_op.drop_column("artifact_summary_json")
        batch_op.drop_column("manifest_path")
        batch_op.drop_column("code_path")
        batch_op.drop_column("result_kind")
        batch_op.drop_column("is_final")
        batch_op.drop_column("parent_turn_id")

    with op.batch_alter_table("v1_conversations", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_v1_conversations_final_turn_id", type_="foreignkey")
        batch_op.drop_index("ix_v1_conversations_final_turn_id")
        batch_op.drop_column("migration_version")
        batch_op.drop_column("branch_summary_json")
        batch_op.drop_column("schema_memory_version")
        batch_op.drop_column("schema_memory_json")
        batch_op.drop_column("final_turn_id")
