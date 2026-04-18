from __future__ import annotations

import duckdb

from agent_v2.tools.search_schema import search_schema


def test_search_schema_discovers_columns_from_workspace_db(tmp_path) -> None:
    db_path = tmp_path / "workspace.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE TABLE orders (order_id INTEGER, customer_name VARCHAR, order_total DOUBLE)")
    finally:
        con.close()

    result = search_schema(
        data_path=str(db_path),
        table_names=["orders"],
        query="customer",
        table_name=None,
        max_results=10,
    )

    columns = result.get("columns") if isinstance(result, dict) else []
    assert isinstance(columns, list)
    assert any(str(item.get("name") or "").strip().lower() == "customer_name" for item in columns)


def test_search_schema_supports_multiple_query_patterns_in_one_call(tmp_path) -> None:
    db_path = tmp_path / "workspace.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            "CREATE TABLE sales (customer_name VARCHAR, total_amount DOUBLE, invoice_date DATE)"
        )
    finally:
        con.close()

    result = search_schema(
        data_path=str(db_path),
        table_names=["sales"],
        query="",
        queries=["customer", "amount"],
        table_name=None,
        max_results=10,
    )

    columns = result.get("columns") if isinstance(result, dict) else []
    assert isinstance(columns, list)
    names = {str(item.get("name") or "").strip().lower() for item in columns}
    assert "customer_name" in names
    assert "total_amount" in names
    first = columns[0] if columns else {}
    assert isinstance(first.get("matched_queries"), list)


def test_search_schema_reports_query_coverage(tmp_path) -> None:
    db_path = tmp_path / "workspace.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("CREATE TABLE sales (customer_name VARCHAR, total_amount DOUBLE)")
    finally:
        con.close()

    result = search_schema(
        data_path=str(db_path),
        table_names=["sales"],
        query="customer",
        queries=["customer", "missing_metric"],
        table_name=None,
        max_results=10,
    )

    covered = result.get("covered_queries") if isinstance(result, dict) else []
    missing = result.get("missing_queries") if isinstance(result, dict) else []
    assert "customer" in (covered or [])
    assert "missing_metric" in (missing or [])
