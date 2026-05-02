from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_turn_tree_metadata_migration_adds_columns_and_keeps_old_inserts_working(tmp_path) -> None:
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

        assert {
            "final_turn_id",
            "schema_memory_json",
            "schema_memory_version",
            "branch_summary_json",
            "migration_version",
        }.issubset(conversation_columns)
        assert {
            "parent_turn_id",
            "is_final",
            "result_kind",
            "code_path",
            "manifest_path",
            "artifact_summary_json",
            "schema_usage_json",
            "execution_summary_json",
        }.issubset(turn_columns)

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
                    "title": "Legacy conversation",
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

            row = conn.execute(
                text(
                    "SELECT final_turn_id, schema_memory_json, schema_memory_version, branch_summary_json, "
                    "migration_version FROM v1_conversations WHERE id = :id"
                ),
                {"id": "conversation-1"},
            ).mappings().one()
            assert row["final_turn_id"] is None
            assert row["schema_memory_json"] is None
            assert row["schema_memory_version"] is None
            assert row["branch_summary_json"] is None
            assert row["migration_version"] is None

            turn_row = conn.execute(
                text(
                    "SELECT parent_turn_id, is_final, result_kind, code_path, manifest_path, "
                    "artifact_summary_json, schema_usage_json, execution_summary_json "
                    "FROM v1_turns WHERE id = :id"
                ),
                {"id": "turn-1"},
            ).mappings().one()
            assert turn_row["parent_turn_id"] is None
            assert turn_row["is_final"] in {0, False}
            assert turn_row["result_kind"] is None
            assert turn_row["code_path"] is None
            assert turn_row["manifest_path"] is None
            assert turn_row["artifact_summary_json"] is None
            assert turn_row["schema_usage_json"] is None
            assert turn_row["execution_summary_json"] is None
    finally:
        engine.dispose()
