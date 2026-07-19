from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.catalog import build_catalog
from inquira_data_worker.errors import AdapterError


def parquet(path: Path, value: str) -> None:
    connection = duckdb.connect()
    try:
        escaped = str(path).replace("'", "''")
        connection.execute(f"COPY (SELECT 1::BIGINT AS id, ?::VARCHAR AS label) TO '{escaped}' (FORMAT PARQUET)", [value])
    finally:
        connection.close()


def test_catalog_builds_queryable_views_for_snapshot_paths_and_unicode_names(tmp_path: Path) -> None:
    north = tmp_path / "north's data.parquet"
    south = tmp_path / "south.parquet"
    parquet(north, "José")
    parquet(south, "東京")
    database = tmp_path / "workspace.duckdb"

    result = build_catalog({
        "database_path": str(database),
        "fingerprint": "catalog:first",
        "tables": [
            {"id": "one", "name": "north_sales", "snapshot_path": str(north)},
            {"id": "two", "name": "東京_sales", "snapshot_path": str(south)},
        ],
    })

    assert result.changed is True
    assert result.table_count == 2
    assert result.byte_size == database.stat().st_size
    connection = duckdb.connect(str(database), read_only=True)
    try:
        assert connection.execute('SELECT label FROM "north_sales"').fetchone()[0] == "José"
        assert connection.execute('SELECT label FROM "東京_sales"').fetchone()[0] == "東京"
    finally:
        connection.close()


def test_catalog_skips_an_unchanged_fingerprint_and_supports_no_tables(tmp_path: Path) -> None:
    database = tmp_path / "empty.duckdb"
    first = build_catalog({"database_path": str(database), "fingerprint": "empty", "tables": []})
    initial_mtime = database.stat().st_mtime_ns
    second = build_catalog({"database_path": str(database), "fingerprint": "empty", "tables": []})
    assert first.changed is True
    assert second.changed is False
    assert second.table_count == 0
    assert database.stat().st_mtime_ns == initial_mtime


def test_catalog_rejects_duplicate_names_and_missing_or_non_parquet_snapshots(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    parquet(source, "ok")
    cases = [
        ([{"id": "1", "name": "same", "snapshot_path": str(source)}, {"id": "2", "name": "same", "snapshot_path": str(source)}], "unique"),
        ([{"id": "1", "name": "missing", "snapshot_path": str(tmp_path / "missing.parquet")}], "does not exist"),
        ([{"id": "1", "name": "wrong", "snapshot_path": str(tmp_path / "wrong.csv")}], "Parquet"),
    ]
    (tmp_path / "wrong.csv").write_text("id\n1\n", encoding="utf-8")
    for index, (tables, message) in enumerate(cases):
        with pytest.raises(AdapterError, match=message):
            build_catalog({"database_path": str(tmp_path / f"bad-{index}.duckdb"), "fingerprint": "bad", "tables": tables})


def test_failed_rebuild_preserves_the_last_good_catalog(tmp_path: Path) -> None:
    source = tmp_path / "source.parquet"
    parquet(source, "good")
    database = tmp_path / "workspace.duckdb"
    build_catalog({
        "database_path": str(database), "fingerprint": "good",
        "tables": [{"id": "1", "name": "data", "snapshot_path": str(source)}],
    })
    before = database.read_bytes()

    with pytest.raises(AdapterError):
        build_catalog({
            "database_path": str(database), "fingerprint": "broken",
            "tables": [{"id": "1", "name": 'bad"name', "snapshot_path": str(tmp_path / "missing.parquet")}],
        })
    assert database.read_bytes() == before
