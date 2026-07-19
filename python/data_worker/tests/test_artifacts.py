from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from inquira_data_worker.artifacts import inspect_parquet, query_parquet
from inquira_data_worker.errors import AdapterError


def _parquet(tmp_path: Path) -> Path:
    path = tmp_path / "sales.parquet"
    connection = duckdb.connect()
    connection.execute(
        "COPY (SELECT * FROM VALUES "
        "(1, 'North', 10.5, DATE '2025-01-01'),"
        "(2, 'South', 30.0, DATE '2025-01-03'),"
        "(3, 'North west', 20.0, DATE '2025-01-02') "
        't("order id", region, amount, sold_on)) TO ? (FORMAT PARQUET)',
        [str(path)],
    )
    connection.close()
    return path


def test_artifact_inspection_and_rows_support_paging_sort_filter_and_search(
    tmp_path: Path,
) -> None:
    path = _parquet(tmp_path)
    metadata = inspect_parquet(str(path))
    assert metadata["row_count"] == 3
    assert [column["name"] for column in metadata["schema"]] == [
        "order id",
        "region",
        "amount",
        "sold_on",
    ]

    page = query_parquet(
        str(path),
        offset=0,
        limit=1,
        sort_model=[{"colId": "amount", "sort": "desc"}],
        filter_model={
            "region": {"filterType": "text", "type": "contains", "filter": "north"}
        },
        search_text="west",
    )
    assert page["row_count"] == 1
    assert page["columns"] == ["order id", "region", "amount", "sold_on"]
    assert page["rows"] == [
        {"order id": 3, "region": "North west", "amount": 20.0, "sold_on": "2025-01-02"}
    ]
    assert page["offset"] == 0 and page["limit"] == 1


def test_artifact_query_ignores_unknown_columns_and_rejects_unsafe_inputs(
    tmp_path: Path,
) -> None:
    path = _parquet(tmp_path)
    page = query_parquet(
        str(path),
        offset=0,
        limit=1000,
        sort_model=[{"colId": "not-a-column", "sort": "desc"}, None],
        filter_model={"not-a-column": {"type": "equals", "filter": "x"}},
    )
    assert [row["order id"] for row in page["rows"]] == [1, 2, 3]

    for bad_path in [
        "relative.parquet",
        str(tmp_path / "missing.parquet"),
        str(tmp_path / "bad.csv"),
    ]:
        if bad_path.endswith("bad.csv"):
            Path(bad_path).write_text("x\n1\n", encoding="utf-8")
        with pytest.raises(AdapterError):
            inspect_parquet(bad_path)
    with pytest.raises(AdapterError):
        query_parquet(str(path), offset=-1, limit=10)
    with pytest.raises(AdapterError):
        query_parquet(str(path), offset=0, limit=1001)


def test_artifact_rows_normalize_non_finite_and_nested_values_for_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "complex.parquet"
    connection = duckdb.connect()
    connection.execute(
        "COPY (SELECT 'NaN'::DOUBLE AS score, [1, 2] AS values) TO ? (FORMAT PARQUET)",
        [str(path)],
    )
    connection.close()
    page = query_parquet(str(path), offset=0, limit=10)
    assert page["rows"] == [{"score": None, "values": [1, 2]}]
