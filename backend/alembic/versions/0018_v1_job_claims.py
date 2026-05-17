"""Add durable claim metadata to background job tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_v1_job_claims"
down_revision = "0017_v1_atomic_turn_seq_and_active_workspace"
branch_labels = None
depends_on = None


def _add_claim_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("claimed_by", sa.String(length=255), nullable=True))
    op.add_column(table_name, sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(table_name, sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(table_name, sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        f"ix_{table_name}_status_lease",
        table_name,
        ["status", "lease_expires_at"],
        unique=False,
    )


def _drop_claim_columns(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_status_lease", table_name=table_name)
    op.drop_column(table_name, "last_heartbeat_at")
    op.drop_column(table_name, "attempt_count")
    op.drop_column(table_name, "lease_expires_at")
    op.drop_column(table_name, "claimed_by")


def upgrade() -> None:
    _add_claim_columns("v1_workspace_deletion_jobs")
    _add_claim_columns("v1_dataset_deletion_jobs")
    _add_claim_columns("v1_dataset_ingestion_jobs")


def downgrade() -> None:
    _drop_claim_columns("v1_dataset_ingestion_jobs")
    _drop_claim_columns("v1_dataset_deletion_jobs")
    _drop_claim_columns("v1_workspace_deletion_jobs")
