"""Add atomic turn sequence and principal active workspace pointer."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_v1_atomic_turn_seq_and_active_workspace"
down_revision = "0016_v1_resource_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "v1_principals",
        sa.Column("active_workspace_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_v1_principals_active_workspace_id",
        "v1_principals",
        ["active_workspace_id"],
        unique=False,
    )
    op.add_column(
        "v1_conversations",
        sa.Column("next_turn_seq", sa.Integer(), nullable=False, server_default="1"),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE v1_conversations
            SET next_turn_seq = COALESCE(
                (
                    SELECT MAX(v1_turns.seq_no) + 1
                    FROM v1_turns
                    WHERE v1_turns.conversation_id = v1_conversations.id
                ),
                1
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE v1_principals
            SET active_workspace_id = (
                SELECT v1_workspaces.id
                FROM v1_workspaces
                WHERE v1_workspaces.owner_principal_id = v1_principals.id
                  AND v1_workspaces.is_active = 1
                ORDER BY v1_workspaces.updated_at DESC, v1_workspaces.id DESC
                LIMIT 1
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_v1_principals_active_workspace_id", table_name="v1_principals")
    op.drop_column("v1_principals", "active_workspace_id")
    op.drop_column("v1_conversations", "next_turn_seq")
