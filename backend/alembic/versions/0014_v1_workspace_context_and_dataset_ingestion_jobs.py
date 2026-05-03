"""Add workspace context and dataset ingestion jobs.

Revision ID: 0014_v1_workspace_context_and_dataset_ingestion_jobs
Revises: 0013_v1_llm_data_samples_preference
Create Date: 2026-05-03
"""

from __future__ import annotations

from alembic import context, op
import sqlalchemy as sa


revision = "0014_v1_workspace_context_and_dataset_ingestion_jobs"
down_revision = "0013_v1_llm_data_samples_preference"
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
    op.add_column(
        "v1_workspaces",
        sa.Column("schema_context", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "v1_dataset_ingestion_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_principal_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_principal_id"], ["v1_principals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_v1_dataset_ingestion_jobs_owner_principal_id",
        "v1_dataset_ingestion_jobs",
        ["owner_principal_id"],
        unique=False,
    )
    op.create_index(
        "ix_v1_ds_ingest_jobs_owner_created",
        "v1_dataset_ingestion_jobs",
        ["owner_principal_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_v1_ds_ingest_jobs_workspace_status",
        "v1_dataset_ingestion_jobs",
        ["workspace_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_index("ix_v1_ds_ingest_jobs_workspace_status", table_name="v1_dataset_ingestion_jobs")
    op.drop_index("ix_v1_ds_ingest_jobs_owner_created", table_name="v1_dataset_ingestion_jobs")
    op.drop_index("ix_v1_dataset_ingestion_jobs_owner_principal_id", table_name="v1_dataset_ingestion_jobs")
    op.drop_table("v1_dataset_ingestion_jobs")
    op.drop_column("v1_workspaces", "schema_context")
