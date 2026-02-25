import sqlite3
from types import SimpleNamespace

from app.v1.services.legacy_cleanup_service import LegacyCleanupService


def _seed_db(path, ddl: str, rows: list[tuple] | None = None):
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(ddl)
        if rows:
            cur.executemany("INSERT INTO users (username) VALUES (?)", rows)
        conn.commit()
    finally:
        conn.close()


def test_cleanup_dry_run_reports_orphans_and_safe_legacy_db(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    base = fake_home / ".inquira"
    base.mkdir(parents=True, exist_ok=True)

    # v1 db with one active username
    v1_db = base / "app_v1.db"
    conn = sqlite3.connect(str(v1_db))
    try:
        cur = conn.cursor()
        cur.executescript("CREATE TABLE v1_users (username TEXT);")
        cur.execute("INSERT INTO v1_users (username) VALUES ('user_live')")
        conn.commit()
    finally:
        conn.close()

    (base / "user_live").mkdir()
    (base / "user_orphan").mkdir()
    (base / "workspaces").mkdir()  # empty legacy folder

    # legacy app.db with users already present in v1 db -> removable
    legacy_db = base / "app.db"
    _seed_db(
        legacy_db,
        "CREATE TABLE users (username TEXT);",
        rows=[("user_live",)],
    )

    monkeypatch.setattr(
        "app.v1.services.legacy_cleanup_service.settings",
        SimpleNamespace(database_url=f"sqlite+aiosqlite:///{v1_db}"),
    )
    monkeypatch.setattr(
        "app.v1.services.legacy_cleanup_service.Path.home",
        staticmethod(lambda: fake_home),
    )

    report = LegacyCleanupService.run_cleanup(dry_run=True)

    assert report.dry_run is True
    assert str(base / "user_orphan") in report.removed_paths
    assert str(base / "user_live") in report.blocked_paths
    assert str(base / "workspaces") in report.removed_paths
    assert str(base / "app.db") in report.removed_paths
    assert (base / "user_orphan").exists() is True
    assert (base / "app.db").exists() is True


def test_cleanup_apply_skips_legacy_db_when_v1_missing_user(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    base = fake_home / ".inquira"
    base.mkdir(parents=True, exist_ok=True)

    v1_db = base / "app_v1.db"
    conn = sqlite3.connect(str(v1_db))
    try:
        cur = conn.cursor()
        cur.executescript("CREATE TABLE v1_users (username TEXT);")
        cur.execute("INSERT INTO v1_users (username) VALUES ('user_live')")
        conn.commit()
    finally:
        conn.close()

    orphan = base / "user_orphan"
    orphan.mkdir()
    legacy_db = base / "app.db"
    _seed_db(
        legacy_db,
        "CREATE TABLE users (username TEXT);",
        rows=[("user_live",), ("user_missing_in_v1",)],
    )

    monkeypatch.setattr(
        "app.v1.services.legacy_cleanup_service.settings",
        SimpleNamespace(database_url=f"sqlite+aiosqlite:///{v1_db}"),
    )
    monkeypatch.setattr(
        "app.v1.services.legacy_cleanup_service.Path.home",
        staticmethod(lambda: fake_home),
    )

    report = LegacyCleanupService.run_cleanup(dry_run=False)

    assert str(orphan) in report.removed_paths
    assert orphan.exists() is False
    assert str(legacy_db) in report.blocked_paths
    assert legacy_db.exists() is True
