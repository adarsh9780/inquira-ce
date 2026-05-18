"""Add schema generation status metadata to workspace datasets."""

from __future__ import annotations

from alembic import context
from alembic import op
import sqlalchemy as sa


revision = "0019_v1_dataset_schema_status_metadata"
down_revision = "0018_v1_job_claims"
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
        "v1_workspace_datasets",
        sa.Column("schema_status", sa.String(length=32), nullable=False, server_default="queued"),
    )
    op.add_column(
        "v1_workspace_datasets",
        sa.Column("schema_error_message", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "v1_workspace_datasets",
        sa.Column("schema_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    if _db_role() == "auth":
        return
    op.drop_column("v1_workspace_datasets", "schema_updated_at")
    op.drop_column("v1_workspace_datasets", "schema_error_message")
    op.drop_column("v1_workspace_datasets", "schema_status")
