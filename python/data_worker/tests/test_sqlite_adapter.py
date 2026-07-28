from __future__ import annotations

import sqlite3
from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.adapters.registry import get_adapter
from inquira_data_worker.errors import AdapterError
from inquira_data_worker.models import AdapterRequest, MaterializeRequest


def create_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE "Sales Data" (
                "order id" INTEGER PRIMARY KEY,
                customer TEXT,
                amount REAL,
                receipt BLOB
            );
            INSERT INTO "Sales Data" VALUES
                (1, 'José', 12.5, X'00FF'),
                (2, '東京', NULL, NULL);
            CREATE TABLE inventory (sku TEXT, quantity INTEGER);
            INSERT INTO inventory VALUES ('A-1', 3), ('B-2', 7);
            CREATE TABLE "odd""name" (value TEXT);
            CREATE VIEW available_inventory AS
                SELECT sku, quantity FROM inventory WHERE quantity > 0;
            """
        )
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize("suffix", [".sqlite", ".SQLITE3", ".db"])
def test_sqlite_discovery_and_preview_are_read_only(suffix: str, tmp_path: Path) -> None:
    path = tmp_path / f"warehouse{suffix}"
    create_database(path)
    before = path.read_bytes()

    adapter = get_adapter("sqlite")
    discovery = adapter.discover(AdapterRequest(source_path=str(path)))
    assert discovery.adapter_kind == "sqlite"
    assert {(item.kind, item.name) for item in discovery.objects} == {
        ("table", "Sales Data"),
        ("table", "inventory"),
        ("table", 'odd"name'),
        ("view", "available_inventory"),
    }
    sales = next(item for item in discovery.objects if item.name == "Sales Data")
    assert sales.id == "table:Sales Data"
    assert [column.name for column in sales.columns] == ["order id", "customer", "amount", "receipt"]
    assert sales.metadata["column_count"] == 4

    preview = adapter.preview(
        AdapterRequest(source_path=str(path), source_object_id=sales.id),
        limit=1,
    )
    assert preview.rows == [{"order id": 1, "customer": "José", "amount": 12.5, "receipt": "00ff"}]
    assert preview.truncated is True
    assert path.read_bytes() == before
    assert not Path(str(path) + "-journal").exists()
    assert not Path(str(path) + "-wal").exists()


def test_sqlite_materializes_selected_tables_and_views_independently(tmp_path: Path) -> None:
    source = tmp_path / "warehouse.sqlite"
    create_database(source)
    target = tmp_path / "snapshot"

    result = get_adapter("sqlite").materialize(MaterializeRequest(
        source_path=str(source),
        target_dir=str(target),
        selected_object_ids=["table:Sales Data", "view:available_inventory"],
    ))

    assert [output.source_object_id for output in result.outputs] == [
        "table:Sales Data",
        "view:available_inventory",
    ]
    assert [output.row_count for output in result.outputs] == [2, 2]
    assert len({output.relative_path for output in result.outputs}) == 2
    for output in result.outputs:
        output_path = target / output.relative_path
        assert output_path.is_file()
        assert output_path.suffix == ".parquet"
        assert duckdb.sql(f"SELECT count(*) FROM read_parquet('{output_path}')").fetchone()[0] == 2


def test_sqlite_fingerprint_changes_when_source_changes(tmp_path: Path) -> None:
    path = tmp_path / "refresh.sqlite"
    create_database(path)
    adapter = get_adapter("sqlite")
    first = adapter.discover(AdapterRequest(source_path=str(path))).fingerprint

    connection = sqlite3.connect(path)
    try:
        connection.execute("INSERT INTO inventory VALUES ('C-3', 9)")
        connection.commit()
    finally:
        connection.close()

    second = adapter.discover(AdapterRequest(source_path=str(path))).fingerprint
    assert second != first


def test_sqlite_rejects_missing_duplicate_and_unknown_selections(tmp_path: Path) -> None:
    path = tmp_path / "selection.sqlite"
    create_database(path)
    adapter = get_adapter("sqlite")

    with pytest.raises(AdapterError, match="at least one"):
        adapter.materialize(MaterializeRequest(
            source_path=str(path),
            target_dir=str(tmp_path / "empty"),
            selected_object_ids=[],
        ))
    with pytest.raises(AdapterError, match="unique"):
        adapter.materialize(MaterializeRequest(
            source_path=str(path),
            target_dir=str(tmp_path / "duplicate"),
            selected_object_ids=["table:inventory", "table:inventory"],
        ))
    with pytest.raises(AdapterError, match="no longer exists"):
        adapter.materialize(MaterializeRequest(
            source_path=str(path),
            target_dir=str(tmp_path / "missing"),
            selected_object_ids=["table:missing"],
        ))


@pytest.mark.parametrize(
    ("name", "payload", "message"),
    [
        ("empty.sqlite", b"", "empty"),
        ("broken.sqlite", b"not sqlite", "sqlite"),
        ("wrong.csv", b"id\n1\n", "extension"),
    ],
)
def test_sqlite_rejects_invalid_sources(
    name: str,
    payload: bytes,
    message: str,
    tmp_path: Path,
) -> None:
    path = tmp_path / name
    path.write_bytes(payload)
    with pytest.raises(AdapterError, match=message):
        get_adapter("sqlite").discover(AdapterRequest(source_path=str(path)))
