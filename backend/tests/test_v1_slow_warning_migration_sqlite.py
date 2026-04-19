from __future__ import annotations

from pathlib import Path


def test_slow_warning_default_migration_uses_sqlite_safe_batch_alter() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "0011_v1_slow_request_warning_default_120.py"
    )
    source = migration_path.read_text(encoding="utf-8")

    assert 'dialect_name == "sqlite"' in source
    assert "batch_alter_table" in source
    assert "server_default=sa.text(\"120\")" in source
    assert "server_default=sa.text(\"30\")" in source
