from __future__ import annotations

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
