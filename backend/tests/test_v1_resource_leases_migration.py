from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_resource_leases_migration_adds_durable_lease_table(tmp_path) -> None:
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
        columns = {column["name"] for column in inspector.get_columns("v1_resource_leases")}
        indexes = {index["name"] for index in inspector.get_indexes("v1_resource_leases")}
        uniques = {tuple(item["column_names"]) for item in inspector.get_unique_constraints("v1_resource_leases")}

        assert {
            "id",
            "resource_key",
            "resource_type",
            "lease_kind",
            "owner_token",
            "leased_until",
            "metadata_json",
            "created_at",
            "updated_at",
        }.issubset(columns)
        assert "ix_v1_resource_leases_type_key" in indexes
        assert "ix_v1_resource_leases_kind_expires" in indexes
        assert ("resource_key", "lease_kind") in uniques

        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO v1_resource_leases "
                    "(id, resource_key, resource_type, lease_kind, owner_token, leased_until, metadata_json) "
                    "VALUES (:id, :resource_key, :resource_type, :lease_kind, :owner_token, CURRENT_TIMESTAMP, :metadata_json)"
                ),
                {
                    "id": "lease-1",
                    "resource_key": "workspace-1",
                    "resource_type": "workspace",
                    "lease_kind": "workspace_runtime",
                    "owner_token": "owner-1",
                    "metadata_json": '{"source":"test"}',
                },
            )
            row = conn.execute(
                text(
                    "SELECT resource_key, resource_type, lease_kind, owner_token, metadata_json "
                    "FROM v1_resource_leases WHERE id = :id"
                ),
                {"id": "lease-1"},
            ).mappings().one()
            assert row["resource_key"] == "workspace-1"
            assert row["lease_kind"] == "workspace_runtime"
            assert row["owner_token"] == "owner-1"
            assert row["metadata_json"] == '{"source":"test"}'
    finally:
        engine.dispose()
