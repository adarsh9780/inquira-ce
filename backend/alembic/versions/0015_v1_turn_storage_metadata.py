"""add turn storage metadata and artifact index

Revision ID: 0015_v1_turn_storage_metadata
Revises: 0014_v1_workspace_context_and_dataset_ingestion_jobs
Create Date: 2026-05-17
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "0015_v1_turn_storage_metadata"
down_revision = "0014_v1_workspace_context_and_dataset_ingestion_jobs"
branch_labels = None
depends_on = None


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
        batch_op.add_column(sa.Column("storage_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("is_marked_for_deletion", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("marked_for_deletion_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deletion_status", sa.String(length=32), nullable=False, server_default="active"))
        batch_op.add_column(sa.Column("deletion_error", sa.String(length=1024), nullable=True))
        batch_op.create_index(
            "ix_v1_conversations_workspace_visible_updated",
            ["workspace_id", "is_marked_for_deletion", "updated_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_v1_conversations_delete_sweep",
            ["is_marked_for_deletion", "marked_for_deletion_at"],
            unique=False,
        )

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("storage_path", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("is_marked_for_deletion", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("marked_for_deletion_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deletion_status", sa.String(length=32), nullable=False, server_default="active"))
        batch_op.add_column(sa.Column("deletion_error", sa.String(length=1024), nullable=True))
        batch_op.create_index(
            "ix_v1_turns_conversation_visible_created",
            ["conversation_id", "is_marked_for_deletion", "created_at", "id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_v1_turns_delete_sweep",
            ["is_marked_for_deletion", "marked_for_deletion_at"],
            unique=False,
        )

    op.create_table(
        "v1_turn_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("logical_name", sa.String(length=255), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column("payload_format", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["v1_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["turn_id"], ["v1_turns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["v1_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_v1_turn_artifacts_workspace_id", "v1_turn_artifacts", ["workspace_id"], unique=False)
    op.create_index("ix_v1_turn_artifacts_conversation_id", "v1_turn_artifacts", ["conversation_id"], unique=False)
    op.create_index("ix_v1_turn_artifacts_turn_id", "v1_turn_artifacts", ["turn_id"], unique=False)
    op.create_index(
        "ix_v1_turn_artifacts_workspace_status_created",
        "v1_turn_artifacts",
        ["workspace_id", "status", "created_at"],
        unique=False,
    )
    op.create_index("ix_v1_turn_artifacts_turn_status", "v1_turn_artifacts", ["turn_id", "status"], unique=False)
    op.create_index(
        "ix_v1_turn_artifacts_conversation_status",
        "v1_turn_artifacts",
        ["conversation_id", "status"],
        unique=False,
    )
    op.create_index("ix_v1_turn_artifacts_delete_sweep", "v1_turn_artifacts", ["status", "deleted_at"], unique=False)


def downgrade() -> None:
    if _db_role() == "auth":
        return

    op.drop_index("ix_v1_turn_artifacts_delete_sweep", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_conversation_status", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_turn_status", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_workspace_status_created", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_turn_id", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_conversation_id", table_name="v1_turn_artifacts")
    op.drop_index("ix_v1_turn_artifacts_workspace_id", table_name="v1_turn_artifacts")
    op.drop_table("v1_turn_artifacts")

    with op.batch_alter_table("v1_turns", recreate="auto") as batch_op:
        batch_op.drop_index("ix_v1_turns_delete_sweep")
        batch_op.drop_index("ix_v1_turns_conversation_visible_created")
        batch_op.drop_column("deletion_error")
        batch_op.drop_column("deletion_status")
        batch_op.drop_column("marked_for_deletion_at")
        batch_op.drop_column("is_marked_for_deletion")
        batch_op.drop_column("storage_path")

    with op.batch_alter_table("v1_conversations", recreate="auto") as batch_op:
        batch_op.drop_index("ix_v1_conversations_delete_sweep")
        batch_op.drop_index("ix_v1_conversations_workspace_visible_updated")
        batch_op.drop_column("deletion_error")
        batch_op.drop_column("deletion_status")
        batch_op.drop_column("marked_for_deletion_at")
        batch_op.drop_column("is_marked_for_deletion")
        batch_op.drop_column("storage_path")
