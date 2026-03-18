from __future__ import annotations

from typing import Any


def safe_table_name(table_name: str) -> str:
    raw = str(table_name or "").strip() or "data"
    return raw.replace('"', '""')


def compose_sql_preview(table_name: str, limit: int = 20) -> str:
    safe = safe_table_name(table_name)
    n = max(1, min(200, int(limit)))
    return f'SELECT * FROM "{safe}" LIMIT {n}'


def analyze_table(table_name: str) -> dict[str, Any]:
    query = compose_sql_preview(table_name)
    code = f'result_df = conn.sql("{query}").fetchdf()\\nresult_df'
    return {
        "code": code,
        "query": query,
        "output_contract": [{"name": "result_df", "kind": "dataframe"}],
    }


def finish(explanation: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "final_explanation": str(explanation or "").strip(),
        "metadata": metadata or {},
    }
