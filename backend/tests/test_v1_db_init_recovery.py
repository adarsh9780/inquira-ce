from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.v1.db.init import _upgrade_or_stamp_schema


def test_upgrade_or_stamp_schema_bootstraps_missing_core_appdata_tables(tmp_path) -> None:
    db_path = tmp_path / "broken_appdata.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(
                text(
                    "INSERT INTO alembic_version (version_num) VALUES ('0016_v1_resource_leases')"
                )
            )
    finally:
        engine.dispose()

    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"
    assert alembic_ini.exists()
    _upgrade_or_stamp_schema(
        alembic_ini=alembic_ini,
        db_role="appdata",
        database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        expected_table="v1_principals",
    )

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "v1_principals",
            "v1_workspaces",
            "v1_conversations",
            "v1_turns",
            "v1_resource_leases",
            "v1_dataset_ingestion_jobs",
        }.issubset(tables)
        with engine.begin() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == "0019_v1_dataset_schema_status_metadata"
    finally:
        engine.dispose()
