"""add workspace AI configuration overrides

Revision ID: 0021_v1_workspace_ai_configuration
Revises: 0020_v1_turn_sibling_order
Create Date: 2026-07-15 00:00:00
"""

from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0021_v1_workspace_ai_configuration"
down_revision: Union[str, Sequence[str], None] = "0020_v1_turn_sibling_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _db_role() -> str:
    cfg_role = str(context.config.attributes.get("inquira_db_role") or "").strip().lower()
    if cfg_role in {"auth", "appdata"}:
        return cfg_role
    x_role = str(context.get_x_argument(as_dictionary=True).get("db", "")).strip().lower()
    return x_role if x_role in {"auth", "appdata"} else "appdata"


def upgrade() -> None:
    if _db_role() == "auth":
        return
    with op.batch_alter_table("v1_workspaces", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("llm_provider_override", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("main_model_override", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("lite_model_override", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("llm_temperature_override", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("llm_max_tokens_override", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("llm_top_p_override", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("allow_llm_data_samples", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("ai_config_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    if _db_role() == "auth":
        return
    with op.batch_alter_table("v1_workspaces", recreate="auto") as batch_op:
        batch_op.drop_column("ai_config_reviewed")
        batch_op.drop_column("allow_llm_data_samples")
        batch_op.drop_column("llm_top_p_override")
        batch_op.drop_column("llm_max_tokens_override")
        batch_op.drop_column("llm_temperature_override")
        batch_op.drop_column("lite_model_override")
        batch_op.drop_column("main_model_override")
        batch_op.drop_column("llm_provider_override")
