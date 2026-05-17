from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_turn_storage_metadata_migration_adds_soft_delete_columns_and_artifact_table(tmp_path) -> None:
    db_path = tmp_path / "appdata_v1.db"
    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = "appdata"

    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        conversation_columns = {column["name"] for column in inspector.get_columns("v1_conversations")}
        turn_columns = {column["name"] for column in inspector.get_columns("v1_turns")}
        artifact_columns = {column["name"] for column in inspector.get_columns("v1_turn_artifacts")}

        assert {
            "storage_path",
            "is_marked_for_deletion",
            "marked_for_deletion_at",
            "deletion_status",
            "deletion_error",
        }.issubset(conversation_columns)
        assert {
            "storage_path",
            "is_marked_for_deletion",
            "marked_for_deletion_at",
            "deletion_status",
            "deletion_error",
        }.issubset(turn_columns)
        assert {
            "id",
            "workspace_id",
            "conversation_id",
            "turn_id",
            "artifact_id",
            "kind",
            "logical_name",
            "storage_path",
            "payload_format",
            "size_bytes",
            "status",
            "created_at",
            "deleted_at",
        }.issubset(artifact_columns)

        conversation_indexes = {index["name"] for index in inspector.get_indexes("v1_conversations")}
        turn_indexes = {index["name"] for index in inspector.get_indexes("v1_turns")}
        artifact_indexes = {index["name"] for index in inspector.get_indexes("v1_turn_artifacts")}

        assert "ix_v1_conversations_workspace_visible_updated" in conversation_indexes
        assert "ix_v1_conversations_delete_sweep" in conversation_indexes
        assert "ix_v1_turns_conversation_visible_created" in turn_indexes
        assert "ix_v1_turns_delete_sweep" in turn_indexes
        assert "ix_v1_turn_artifacts_workspace_status_created" in artifact_indexes
        assert "ix_v1_turn_artifacts_turn_status" in artifact_indexes
        assert "ix_v1_turn_artifacts_conversation_status" in artifact_indexes
        assert "ix_v1_turn_artifacts_delete_sweep" in artifact_indexes

        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO v1_principals (id, username_cached, plan_cached) "
                    "VALUES (:id, :username_cached, :plan_cached)"
                ),
                {"id": "principal-1", "username_cached": "alice", "plan_cached": "FREE"},
            )
            conn.execute(
                text(
                    "INSERT INTO v1_workspaces "
                    "(id, owner_principal_id, name, name_normalized, is_active, duckdb_path) "
                    "VALUES (:id, :owner_principal_id, :name, :name_normalized, :is_active, :duckdb_path)"
                ),
                {
                    "id": "workspace-1",
                    "owner_principal_id": "principal-1",
                    "name": "Workspace",
                    "name_normalized": "workspace",
                    "is_active": 1,
                    "duckdb_path": "/tmp/test.duckdb",
                },
            )
            conn.execute(
                text(
                    "INSERT INTO v1_conversations (id, workspace_id, title, created_by_principal_id) "
                    "VALUES (:id, :workspace_id, :title, :created_by_principal_id)"
                ),
                {
                    "id": "conversation-1",
                    "workspace_id": "workspace-1",
                    "title": "Storage Conversation",
                    "created_by_principal_id": "principal-1",
                },
            )
            conn.execute(
                text(
                    "INSERT INTO v1_turns "
                    "(id, conversation_id, seq_no, user_text, assistant_text) "
                    "VALUES (:id, :conversation_id, :seq_no, :user_text, :assistant_text)"
                ),
                {
                    "id": "turn-1",
                    "conversation_id": "conversation-1",
                    "seq_no": 1,
                    "user_text": "hello",
                    "assistant_text": "world",
                },
            )
            conn.execute(
                text(
                    "INSERT INTO v1_turn_artifacts "
                    "(id, workspace_id, conversation_id, turn_id, artifact_id, kind, storage_path, payload_format) "
                    "VALUES (:id, :workspace_id, :conversation_id, :turn_id, :artifact_id, :kind, :storage_path, :payload_format)"
                ),
                {
                    "id": "artifact-row-1",
                    "workspace_id": "workspace-1",
                    "conversation_id": "conversation-1",
                    "turn_id": "turn-1",
                    "artifact_id": "artifact-1",
                    "kind": "dataframe",
                    "storage_path": "/tmp/artifacts/orders.parquet",
                    "payload_format": "parquet",
                },
            )

            conversation_row = conn.execute(
                text(
                    "SELECT storage_path, is_marked_for_deletion, marked_for_deletion_at, deletion_status, deletion_error "
                    "FROM v1_conversations WHERE id = :id"
                ),
                {"id": "conversation-1"},
            ).mappings().one()
            assert conversation_row["storage_path"] is None
            assert conversation_row["is_marked_for_deletion"] in {0, False}
            assert conversation_row["marked_for_deletion_at"] is None
            assert conversation_row["deletion_status"] == "active"
            assert conversation_row["deletion_error"] is None

            turn_row = conn.execute(
                text(
                    "SELECT storage_path, is_marked_for_deletion, marked_for_deletion_at, deletion_status, deletion_error "
                    "FROM v1_turns WHERE id = :id"
                ),
                {"id": "turn-1"},
            ).mappings().one()
            assert turn_row["storage_path"] is None
            assert turn_row["is_marked_for_deletion"] in {0, False}
            assert turn_row["marked_for_deletion_at"] is None
            assert turn_row["deletion_status"] == "active"
            assert turn_row["deletion_error"] is None

            artifact_row = conn.execute(
                text(
                    "SELECT logical_name, size_bytes, status, deleted_at "
                    "FROM v1_turn_artifacts WHERE id = :id"
                ),
                {"id": "artifact-row-1"},
            ).mappings().one()
            assert artifact_row["logical_name"] is None
            assert artifact_row["size_bytes"] is None
            assert artifact_row["status"] == "active"
            assert artifact_row["deleted_at"] is None
    finally:
        engine.dispose()
