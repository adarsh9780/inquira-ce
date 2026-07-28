from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.adapters.registry import get_adapter
from inquira_data_worker.errors import AdapterError
from inquira_data_worker.models import AdapterRequest, MaterializeRequest


def write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(rows)


def write_parquet(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    try:
        escaped = str(path).replace("'", "''")
        connection.execute(
            f"""COPY (
                SELECT 1::BIGINT AS id, 'alpha'::VARCHAR AS label, DATE '2026-07-17' AS occurred_on
                UNION ALL
                SELECT 2::BIGINT, NULL::VARCHAR, DATE '2026-07-18'
            ) TO '{escaped}' (FORMAT PARQUET)"""
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("kind", "suffix"),
    [
        ("csv", ".csv"),
        ("CSV", ".CSV"),
        ("parquet", ".parquet"),
        ("PARQUET", ".PARQUET"),
        ("json", ".json"),
        ("JSON", ".JSONL"),
    ],
)
def test_registry_resolves_supported_adapters_case_insensitively(kind: str, suffix: str, tmp_path: Path) -> None:
    path = tmp_path / f"source{suffix}"
    if kind.lower() == "csv":
        write_csv(path, [["id"], [1]])
    elif kind.lower() == "parquet":
        write_parquet(path)
    else:
        path.write_text('[{"id": 1}]' if suffix.lower() == ".json" else '{"id": 1}\n', encoding="utf-8")
    result = get_adapter(kind).discover(AdapterRequest(source_path=str(path)))
    assert result.adapter_kind == kind.lower()
    assert result.source_path == str(path.resolve())
    assert len(result.objects) == 1


@pytest.mark.parametrize("kind", ["postgres", "unknown", ""])
def test_registry_rejects_unimplemented_adapters(kind: str) -> None:
    with pytest.raises(AdapterError, match="not supported"):
        get_adapter(kind)


@pytest.mark.parametrize("kind,suffix", [("csv", ".csv"), ("parquet", ".parquet")])
def test_adapter_rejects_missing_and_directory_sources(kind: str, suffix: str, tmp_path: Path) -> None:
    adapter = get_adapter(kind)
    with pytest.raises(AdapterError, match="does not exist"):
        adapter.discover(AdapterRequest(source_path=str(tmp_path / f"missing{suffix}")))
    with pytest.raises(AdapterError, match="regular file"):
        adapter.discover(AdapterRequest(source_path=str(tmp_path)))


@pytest.mark.parametrize("kind,bad_suffix", [("csv", ".parquet"), ("parquet", ".csv")])
def test_adapter_rejects_extension_mismatches(kind: str, bad_suffix: str, tmp_path: Path) -> None:
    path = tmp_path / f"wrong{bad_suffix}"
    path.write_bytes(b"not the requested format")
    with pytest.raises(AdapterError, match="extension"):
        get_adapter(kind).discover(AdapterRequest(source_path=str(path)))


@pytest.mark.parametrize("kind,suffix", [("csv", ".csv"), ("parquet", ".parquet")])
def test_adapter_reports_empty_or_corrupt_sources(kind: str, suffix: str, tmp_path: Path) -> None:
    path = tmp_path / f"broken{suffix}"
    path.write_bytes(b"" if kind == "csv" else b"not parquet")
    with pytest.raises(AdapterError, match="read"):
        get_adapter(kind).discover(AdapterRequest(source_path=str(path)))


def test_csv_discovery_and_preview_preserve_quotes_unicode_and_nulls(tmp_path: Path) -> None:
    path = tmp_path / "Quarterly ünicode data.csv"
    write_csv(
        path,
        [
            ["id", "customer", "comment", "amount"],
            [1, "José", "contains, comma", "12.50"],
            [2, "東京", 'contains "quote"', ""],
            [3, "Ada", "line one\nline two", "8.25"],
        ],
    )
    adapter = get_adapter("csv")
    discovery = adapter.discover(AdapterRequest(source_path=str(path)))
    assert discovery.objects[0].id == "file"
    assert discovery.objects[0].name == "Quarterly ünicode data"
    assert [column.name for column in discovery.objects[0].columns] == ["id", "customer", "comment", "amount"]
    assert discovery.fingerprint

    preview = adapter.preview(AdapterRequest(source_path=str(path)), limit=2)
    assert preview.columns == discovery.objects[0].columns
    assert len(preview.rows) == 2
    assert preview.rows[0]["customer"] == "José"
    assert preview.rows[0]["comment"] == "contains, comma"
    assert preview.truncated is True


@pytest.mark.parametrize("limit", [0, -1, 1001])
def test_preview_rejects_invalid_or_excessive_limits(limit: int, tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    write_csv(path, [["id"], [1]])
    with pytest.raises(AdapterError, match="limit"):
        get_adapter("csv").preview(AdapterRequest(source_path=str(path)), limit=limit)


def test_parquet_discovery_and_preview_preserve_types_and_nulls(tmp_path: Path) -> None:
    path = tmp_path / "events.parquet"
    write_parquet(path)
    adapter = get_adapter("parquet")
    discovery = adapter.discover(AdapterRequest(source_path=str(path)))
    assert [(column.name, column.data_type) for column in discovery.objects[0].columns] == [
        ("id", "BIGINT"),
        ("label", "VARCHAR"),
        ("occurred_on", "DATE"),
    ]
    preview = adapter.preview(AdapterRequest(source_path=str(path)), limit=10)
    assert len(preview.rows) == 2
    assert preview.rows[1]["label"] is None
    assert preview.rows[0]["occurred_on"] == "2026-07-17"
    assert preview.truncated is False


@pytest.mark.parametrize("kind", ["csv", "parquet"])
def test_materialization_writes_canonical_parquet_without_an_ingestion_limit(kind: str, tmp_path: Path) -> None:
    source = tmp_path / ("many rows.csv" if kind == "csv" else "many rows.parquet")
    if kind == "csv":
        write_csv(source, [["id", "value"], *[[index, f"row-{index}"] for index in range(257)]])
    else:
        escaped = str(source).replace("'", "''")
        duckdb.sql(f"COPY (SELECT range AS id FROM range(257)) TO '{escaped}' (FORMAT PARQUET)")

    target = tmp_path / "staging output"
    result = get_adapter(kind).materialize(
        MaterializeRequest(source_path=str(source), target_dir=str(target), selected_object_ids=["file"])
    )
    assert result.fingerprint
    assert len(result.outputs) == 1
    output = result.outputs[0]
    assert output.relative_path == "data.parquet"
    assert output.row_count == 257
    assert output.byte_size > 0
    assert duckdb.sql(f"SELECT count(*) FROM read_parquet('{target / output.relative_path}')").fetchone()[0] == 257


def test_materialization_requires_the_file_object_and_an_empty_target(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    write_csv(source, [["id"], [1]])
    adapter = get_adapter("csv")
    with pytest.raises(AdapterError, match="file"):
        adapter.materialize(MaterializeRequest(source_path=str(source), target_dir=str(tmp_path / "one"), selected_object_ids=[]))
    with pytest.raises(AdapterError, match="file"):
        adapter.materialize(MaterializeRequest(source_path=str(source), target_dir=str(tmp_path / "two"), selected_object_ids=["other"]))
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(AdapterError, match="empty"):
        adapter.materialize(MaterializeRequest(source_path=str(source), target_dir=str(occupied), selected_object_ids=["file"]))
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_fingerprint_is_stable_until_source_content_changes(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    write_csv(path, [["id"], [1]])
    adapter = get_adapter("csv")
    first = adapter.discover(AdapterRequest(source_path=str(path))).fingerprint
    second = adapter.discover(AdapterRequest(source_path=str(path))).fingerprint
    assert first == second
    write_csv(path, [["id"], [1], [2]])
    third = adapter.discover(AdapterRequest(source_path=str(path))).fingerprint
    assert third != first
