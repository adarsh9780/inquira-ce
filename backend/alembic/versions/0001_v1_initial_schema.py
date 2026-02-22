"""v1 initial schema

Revision ID: 0001_v1_initial_schema
Revises: None
Create Date: 2026-02-21 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_v1_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "v1_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.Enum("FREE", "PAID", name="userplan"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_v1_users_username", "v1_users", ["username"], unique=True)

    op.create_table(
        "v1_user_sessions",
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["v1_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_token"),
    )
    op.create_index("ix_v1_user_sessions_user_id", "v1_user_sessions", ["user_id"], unique=False)

    op.create_table(
        "v1_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_normalized", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("duckdb_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["v1_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name_normalized", name="uq_v1_workspace_user_name_norm"),
    )
    op.create_index("ix_v1_workspaces_user_id", "v1_workspaces", ["user_id"], unique=False)

    op.create_table(
        "v1_workspace_datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("table_name", sa.String(length=255), nullable=False),
        sa.Column("schema_path", sa.String(length=1024), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("source_mtime", sa.Float(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("file_type", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["v1_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "source_fingerprint", name="uq_v1_ws_fingerprint"),
        sa.UniqueConstraint("workspace_id", "table_name", name="uq_v1_ws_table_name"),
    )
    op.create_index("ix_v1_workspace_datasets_workspace_id", "v1_workspace_datasets", ["workspace_id"], unique=False)

    op.create_table(
        "v1_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("last_turn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["v1_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["v1_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_v1_conversations_workspace_id", "v1_conversations", ["workspace_id"], unique=False)
    op.create_index("ix_v1_conversations_created_by_user_id", "v1_conversations", ["created_by_user_id"], unique=False)
    op.create_index("ix_v1_conversations_workspace_updated", "v1_conversations", ["workspace_id", "updated_at"], unique=False)

    op.create_table(
        "v1_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("seq_no", sa.Integer(), nullable=False),
        sa.Column("user_text", sa.String(), nullable=False),
        sa.Column("assistant_text", sa.String(), nullable=False),
        sa.Column("tool_events_json", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.Column("code_snapshot", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["v1_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "seq_no", name="uq_v1_turn_seq"),
    )
    op.create_index("ix_v1_turns_conversation_id", "v1_turns", ["conversation_id"], unique=False)
    op.create_index("ix_v1_turns_conversation_created", "v1_turns", ["conversation_id", "created_at", "id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_v1_turns_conversation_created", table_name="v1_turns")
    op.drop_index("ix_v1_turns_conversation_id", table_name="v1_turns")
    op.drop_table("v1_turns")

    op.drop_index("ix_v1_conversations_workspace_updated", table_name="v1_conversations")
    op.drop_index("ix_v1_conversations_created_by_user_id", table_name="v1_conversations")
    op.drop_index("ix_v1_conversations_workspace_id", table_name="v1_conversations")
    op.drop_table("v1_conversations")

    op.drop_index("ix_v1_workspace_datasets_workspace_id", table_name="v1_workspace_datasets")
    op.drop_table("v1_workspace_datasets")

    op.drop_index("ix_v1_workspaces_user_id", table_name="v1_workspaces")
    op.drop_table("v1_workspaces")

    op.drop_index("ix_v1_user_sessions_user_id", table_name="v1_user_sessions")
    op.drop_table("v1_user_sessions")

    op.drop_index("ix_v1_users_username", table_name="v1_users")
    op.drop_table("v1_users")

    op.execute("DROP TYPE IF EXISTS userplan")
