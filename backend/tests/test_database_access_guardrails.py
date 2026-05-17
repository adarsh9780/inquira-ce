from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
DOC_PATH = ROOT / "docs" / "database-access.md"

ALLOWED_DUCKDB_FILE_CONNECT_PATHS = {
    Path("app/data_access/workspace_db.py"),
    Path("app/services/artifact_scratchpad.py"),
    Path("app/services/workspace_kernel_manager.py"),
}
ALLOWED_SQLITE3_CONNECT_PATHS = {
    Path("app/v1/services/legacy_cleanup_service.py"),
}


def test_file_backed_duckdb_connect_is_limited_to_approved_modules() -> None:
    violations: list[str] = []
    pattern = re.compile(r"duckdb\.connect\(\s*[^)\s]")

    for path in APP_ROOT.rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in ALLOWED_DUCKDB_FILE_CONNECT_PATHS:
            continue
        content = path.read_text(encoding="utf-8")
        if pattern.search(content):
            violations.append(str(rel_path))

    assert violations == [], (
        "Raw file-backed duckdb.connect() calls must stay inside approved modules. "
        f"Violations: {violations}"
    )


def test_sqlite3_connect_is_limited_to_legacy_cleanup_module() -> None:
    violations: list[str] = []
    pattern = re.compile(r"sqlite3\.connect\(")

    for path in APP_ROOT.rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in ALLOWED_SQLITE3_CONNECT_PATHS:
            continue
        content = path.read_text(encoding="utf-8")
        if pattern.search(content):
            violations.append(str(rel_path))

    assert violations == [], (
        "Raw sqlite3.connect() calls must stay inside approved modules. "
        f"Violations: {violations}"
    )


def test_database_access_docs_cover_registered_resources() -> None:
    content = DOC_PATH.read_text(encoding="utf-8")
    for resource_name in (
        "auth_sqlite",
        "appdata_sqlite",
        "workspace_duckdb",
        "scratchpad_duckdb",
        "turn_blob_store",
    ):
        assert resource_name in content
    assert "runtime adapter" in content.lower()
    assert "offline adapter" in content.lower()
    assert "DatabaseSpec" in content
