from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _migration_config(db_path: Path, db_role: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.attributes["inquira_db_role"] = db_role
    return cfg


def test_llm_data_samples_migration_is_appdata_only(tmp_path) -> None:
    auth_db_path = tmp_path / "auth_v1.db"
    command.upgrade(_migration_config(auth_db_path, "auth"), "head")

    auth_engine = create_engine(f"sqlite:///{auth_db_path.as_posix()}")
    try:
        auth_tables = set(inspect(auth_engine).get_table_names())
        assert "v1_user_preferences" not in auth_tables
    finally:
        auth_engine.dispose()

    appdata_db_path = tmp_path / "appdata_v1.db"
    command.upgrade(_migration_config(appdata_db_path, "appdata"), "head")

    appdata_engine = create_engine(f"sqlite:///{appdata_db_path.as_posix()}")
    try:
        columns = {
            column["name"]
            for column in inspect(appdata_engine).get_columns("v1_user_preferences")
        }
        assert "allow_llm_data_samples" in columns
    finally:
        appdata_engine.dispose()
