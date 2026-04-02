from __future__ import annotations

import pytest

import duckdb

from app.services.artifact_scratchpad import ArtifactScratchpadStore


def test_store_script_and_fetch_metadata(tmp_path):
    workspace_db = tmp_path / "ws" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    artifact_id = store.store_script_artifact(
        workspace_duckdb_path=str(workspace_db),
        workspace_id="ws-1",
        run_id="run-1",
        script_text="print('hello')\n",
    )

    metadata = store.get_artifact(
        workspace_duckdb_path=str(workspace_db),
        artifact_id=artifact_id,
    )

    assert metadata is not None
    assert metadata["artifact_id"] == artifact_id
    assert metadata["kind"] == "script"
    assert metadata["payload"]["script"] == "print('hello')\n"


def test_get_dataframe_rows_reads_manifest_table(tmp_path):
    workspace_db = tmp_path / "ws2" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        con.execute("CREATE TABLE art_run_1 (a INTEGER)")
        con.execute("INSERT INTO art_run_1 VALUES (1), (2), (3)")
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'a1', 'run-1', 'ws-1', 'summary', 'dataframe', 'art_run_1',
                NULL, NULL, 3, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
    finally:
        con.close()

    rows = store.get_dataframe_rows(
        workspace_duckdb_path=str(workspace_db),
        artifact_id="a1",
        offset=1,
        limit=2,
    )

    assert rows is not None
    assert rows["artifact_id"] == "a1"
    assert rows["row_count"] == 3
    assert rows["rows"] == [{"a": 2}, {"a": 3}]


def test_get_dataframe_rows_applies_sort_filter_and_global_search(tmp_path):
    workspace_db = tmp_path / "ws2-search-sort" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        con.execute("CREATE TABLE art_run_search (name VARCHAR, city VARCHAR, amount INTEGER)")
        con.execute(
            """
            INSERT INTO art_run_search VALUES
            ('Alice', 'New York', 50),
            ('Bob', 'Boston', 75),
            ('Carol', 'New Delhi', 65),
            ('Dan', 'Austin', 90)
            """
        )
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'a2', 'run-2', 'ws-2', 'summary', 'dataframe', 'art_run_search',
                NULL, NULL, 4, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
    finally:
        con.close()

    rows = store.get_dataframe_rows(
        workspace_duckdb_path=str(workspace_db),
        artifact_id="a2",
        offset=0,
        limit=10,
        sort_model=[{"colId": "amount", "sort": "desc"}],
        filter_model={
            "name": {
                "filterType": "text",
                "type": "contains",
                "filter": "a",
            }
        },
        search_text="new",
    )

    assert rows is not None
    assert rows["row_count"] == 2
    assert [item["name"] for item in rows["rows"]] == ["Carol", "Alice"]


def test_delete_artifact_removes_manifest_row_and_dataframe_table(tmp_path):
    workspace_db = tmp_path / "ws-del" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        con.execute("CREATE TABLE art_to_delete (a INTEGER)")
        con.execute("INSERT INTO art_to_delete VALUES (1), (2)")
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'df-del', 'run-del', 'ws-del', 'summary', 'dataframe', 'art_to_delete',
                NULL, NULL, 2, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
    finally:
        con.close()

    deleted = store.delete_artifact(
        workspace_duckdb_path=str(workspace_db),
        artifact_id="df-del",
    )
    assert deleted is True

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        manifest_count = con.execute(
            "SELECT COUNT(*) FROM artifact_manifest WHERE artifact_id = 'df-del'"
        ).fetchone()[0]
        table_count = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'art_to_delete'"
        ).fetchone()[0]
    finally:
        con.close()

    assert manifest_count == 0
    assert table_count == 0


def test_delete_artifact_returns_false_when_missing(tmp_path):
    workspace_db = tmp_path / "ws-del-missing" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    store.ensure_workspace(str(workspace_db))

    deleted = store.delete_artifact(
        workspace_duckdb_path=str(workspace_db),
        artifact_id="missing-id",
    )
    assert deleted is False


def test_prune_workspace_ignores_duckdb_lock_conflict(monkeypatch, tmp_path):
    workspace_db = tmp_path / "ws3" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.build_scratchpad_db_path(str(workspace_db))
    scratchpad_db.parent.mkdir(parents=True, exist_ok=True)
    scratchpad_db.touch()

    def _raise_lock(*_args, **_kwargs):
        raise duckdb.IOException("Conflicting lock is held")

    monkeypatch.setattr(duckdb, "connect", _raise_lock)

    # Should be a no-op when another process owns the lock.
    store.prune_workspace(workspace_duckdb_path=str(workspace_db))


def test_is_lock_conflict_detects_windows_duckdb_message():
    exc = duckdb.IOException(
        'IO Error: Cannot open file "C:\\temp\\artifacts.duckdb": '
        "The process cannot access the file because it is being used by another process."
    )
    assert ArtifactScratchpadStore._is_lock_conflict(exc) is True


def _insert_dataframe_artifact(con, artifact_id, logical_name, expires_offset="+ INTERVAL 1 DAY"):
    con.execute(
        f"""
        INSERT INTO artifact_manifest (
            artifact_id, run_id, workspace_id, logical_name, kind, table_name,
            payload_json, schema_json, row_count, created_at, expires_at, status, error
        ) VALUES (
            '{artifact_id}', 'run-list', 'ws-list', '{logical_name}', 'dataframe', 'tbl_{artifact_id}',
            NULL, NULL, 10, NOW(), NOW() {expires_offset}, 'ready', NULL
        )
        """
    )


def test_list_artifacts_for_workspace_returns_only_dataframes(tmp_path):
    """list_artifacts_for_workspace(kind='dataframe') should exclude non-dataframe kinds."""
    workspace_db = tmp_path / "ws4" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        # Dataframe artifact
        _insert_dataframe_artifact(con, "df-1", "my_table")

        # Script artifact — should NOT appear when filtering by 'dataframe'
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'sc-1', 'run-list', 'ws-list', 'final_script', 'script', NULL,
                '{"script": "pass"}', NULL, NULL, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
    finally:
        con.close()

    results = store.list_artifacts_for_workspace(
        workspace_duckdb_path=str(workspace_db),
        kind="dataframe",
    )

    assert len(results) == 1
    assert results[0]["artifact_id"] == "df-1"
    assert results[0]["logical_name"] == "my_table"
    assert results[0]["kind"] == "dataframe"


def test_list_artifacts_for_workspace_excludes_expired(tmp_path):
    """list_artifacts_for_workspace should not return artifacts past their expires_at."""
    workspace_db = tmp_path / "ws5" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        # Non-expired
        _insert_dataframe_artifact(con, "df-fresh", "fresh_table", "+ INTERVAL 1 DAY")
        # Expired
        _insert_dataframe_artifact(con, "df-old", "old_table", "- INTERVAL 1 DAY")
    finally:
        con.close()

    results = store.list_artifacts_for_workspace(
        workspace_duckdb_path=str(workspace_db),
        kind="dataframe",
    )

    ids = [r["artifact_id"] for r in results]
    assert "df-fresh" in ids
    assert "df-old" not in ids


def test_list_artifacts_for_workspace_no_kind_filter(tmp_path):
    """list_artifacts_for_workspace without kind filter returns all non-expired ready artifacts."""
    workspace_db = tmp_path / "ws6" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        _insert_dataframe_artifact(con, "df-a", "table_a")
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'sc-a', 'run-list', 'ws-list', 'script_a', 'script', NULL,
                '{"script": "pass"}', NULL, NULL, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
    finally:
        con.close()

    results = store.list_artifacts_for_workspace(workspace_duckdb_path=str(workspace_db))
    kinds = {r["kind"] for r in results}
    assert "dataframe" in kinds
    assert "script" in kinds


def test_get_workspace_artifact_usage_reports_duckdb_bytes_and_ready_figure_count(tmp_path):
    workspace_db = tmp_path / "ws_usage" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'fig-ready', 'run-usage', 'ws-usage', 'chart_a', 'figure', NULL,
                '{"figure": {"data": []}}', NULL, NULL, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'fig-expired', 'run-usage', 'ws-usage', 'chart_old', 'figure', NULL,
                '{"figure": {"data": []}}', NULL, NULL, NOW(), NOW() - INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'fig-failed', 'run-usage', 'ws-usage', 'chart_failed', 'figure', NULL,
                '{"figure": {"data": []}}', NULL, NULL, NOW(), NOW() + INTERVAL 1 DAY, 'error', 'failed'
            )
            """
        )
    finally:
        con.close()

    usage = store.get_workspace_artifact_usage(workspace_duckdb_path=str(workspace_db))
    assert usage["duckdb_bytes"] > 0
    assert usage["figure_count"] == 1


def test_list_artifacts_for_workspace_deduplicates_by_logical_name(tmp_path):
    """Regression: the UNIQUE(workspace_id, kind, logical_name) constraint must prevent duplicate rows.

    Before the fix, export_dataframe always did a plain INSERT with a new UUID,
    causing N rows for N runs of the same query — this is the root cause of the
    '22 tables with the same name' bug.

    The schema-level UNIQUE constraint makes this visible immediately: a second
    INSERT for the same (workspace_id, kind, logical_name) raises a constraint
    violation instead of silently accumulating rows.
    """
    workspace_db = tmp_path / "ws7" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    con = duckdb.connect(str(scratchpad_db), read_only=False)
    try:
        # First export of 'results' for this workspace — must succeed.
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'first-id', 'run-1', 'ws-dedup', 'results', 'dataframe', 'tbl_first',
                NULL, NULL, 5, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )

        # Second export of the same 'results' name WITHOUT deleting the first row MUST fail.
        # This is what export_dataframe used to do (plain INSERT), and it proves the
        # UNIQUE constraint catches it.
        raised = False
        try:
            con.execute(
                """
                INSERT INTO artifact_manifest (
                    artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                    payload_json, schema_json, row_count, created_at, expires_at, status, error
                ) VALUES (
                    'second-id', 'run-2', 'ws-dedup', 'results', 'dataframe', 'tbl_second',
                    NULL, NULL, 10, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
                )
                """
            )
        except Exception:
            raised = True

        assert raised, (
            "Expected a UNIQUE constraint violation when inserting a second artifact "
            "with the same (workspace_id, kind, logical_name). "
            "This means the schema does NOT enforce uniqueness — duplicates will accumulate."
        )

        # Verify only one row exists after the failed duplicate insert.
        count = con.execute(
            "SELECT COUNT(*) FROM artifact_manifest WHERE workspace_id = 'ws-dedup' AND logical_name = 'results'"
        ).fetchone()[0]
        assert count == 1, f"Expected 1 artifact for 'results', got {count}"

        # Now simulate the correct upsert: DELETE old + INSERT new — this must succeed.
        con.execute("DELETE FROM artifact_manifest WHERE artifact_id = 'first-id'")
        con.execute(
            """
            INSERT INTO artifact_manifest (
                artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                payload_json, schema_json, row_count, created_at, expires_at, status, error
            ) VALUES (
                'replaced-id', 'run-2', 'ws-dedup', 'results', 'dataframe', 'tbl_replaced',
                NULL, NULL, 10, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
            )
            """
        )

        # After upsert: still exactly one row, and it's the new one.
        row = con.execute(
            "SELECT artifact_id FROM artifact_manifest WHERE workspace_id = 'ws-dedup' AND logical_name = 'results'"
        ).fetchone()
        assert row is not None
        assert row[0] == "replaced-id", f"Expected 'replaced-id' after upsert, got '{row[0]}'"

    finally:
        con.close()


def test_read_only_methods_succeed_without_lock(tmp_path):
    """Read-only methods should work directly when no write lock is held.

    This verifies the refactoring: read-only methods use ``_open_readonly()``
    instead of ``ensure_workspace()`` and succeed for normal read access.
    """
    workspace_db = tmp_path / "ws_ro" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    # Seed data with a write connection, then close it.
    con = duckdb.connect(str(scratchpad_db), read_only=False)
    con.execute("CREATE TABLE art_ro (x INTEGER)")
    con.execute("INSERT INTO art_ro VALUES (1), (2)")
    con.execute(
        """
        INSERT INTO artifact_manifest (
            artifact_id, run_id, workspace_id, logical_name, kind, table_name,
            payload_json, schema_json, row_count, created_at, expires_at, status, error
        ) VALUES (
            'ro-test', 'run-ro', 'ws-ro', 'ro_table', 'dataframe', 'art_ro',
            NULL, NULL, 2, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL
        )
        """
    )
    con.close()

    # All three read-only methods work WITHOUT calling ensure_workspace() again.
    artifacts = store.list_artifacts_for_workspace(
        workspace_duckdb_path=str(workspace_db), kind="dataframe"
    )
    assert len(artifacts) == 1
    assert artifacts[0]["logical_name"] == "ro_table"

    meta = store.get_artifact(workspace_duckdb_path=str(workspace_db), artifact_id="ro-test")
    assert meta is not None
    assert meta["kind"] == "dataframe"

    rows = store.get_dataframe_rows(
        workspace_duckdb_path=str(workspace_db), artifact_id="ro-test", offset=0, limit=10
    )
    assert rows is not None
    assert rows["row_count"] == 2


def test_read_only_methods_raise_ioerror_under_cross_process_lock(tmp_path):
    """Regression: read-only methods raise IOException under a cross-process write lock.

    The kernel holds a persistent write connection in its subprocess.  DuckDB
    disallows even read-only connections from another process when a writer is
    active.  Read-only methods raise ``duckdb.IOException`` which the API layer
    catches and falls back to the kernel's in-process scratchpad connection.
    """
    import subprocess
    import sys

    workspace_db = tmp_path / "ws_lock" / "workspace.duckdb"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    workspace_db.touch()

    store = ArtifactScratchpadStore()
    scratchpad_db = store.ensure_workspace(str(workspace_db))

    import textwrap
    child_script = textwrap.dedent(f"""\
import duckdb, sys
conn = duckdb.connect(r'{scratchpad_db}', read_only=False)
conn.execute("CREATE TABLE IF NOT EXISTS art_data (x INTEGER)")
conn.execute("INSERT INTO art_data VALUES (10), (20), (30)")
conn.execute(
    "INSERT INTO artifact_manifest "
    "(artifact_id, run_id, workspace_id, logical_name, kind, table_name, "
    "payload_json, schema_json, row_count, created_at, expires_at, status, error) "
    "VALUES ('lock-test', 'run-lock', 'ws-lock', 'locked_table', 'dataframe', 'art_data', "
    "NULL, NULL, 3, NOW(), NOW() + INTERVAL 1 DAY, 'ready', NULL)"
)
print("READY", flush=True)
sys.stdin.readline()
conn.close()
""")

    proc = subprocess.Popen(
        [sys.executable, "-c", child_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        line = proc.stdout.readline().strip()
        if line != "READY":
            err = proc.stderr.read()
            raise AssertionError(f"Child did not become ready, got: {line!r}, stderr: {err}")

        # Read-only methods should raise IOException (lock conflict), which the
        # API layer catches and falls back to the kernel.
        with pytest.raises(duckdb.IOException) as exc_info:
            store.list_artifacts_for_workspace(
                workspace_duckdb_path=str(workspace_db), kind="dataframe"
            )
        assert ArtifactScratchpadStore._is_lock_conflict(exc_info.value)
    finally:
        proc.stdin.write("done\n")
        proc.stdin.flush()
        proc.wait(timeout=5)
