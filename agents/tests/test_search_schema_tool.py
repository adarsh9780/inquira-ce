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
