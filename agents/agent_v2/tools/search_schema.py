"""Schema retrieval tool for agent v2."""

from __future__ import annotations

from typing import Any

import duckdb

from ..events import emit_agent_event
from . import new_tool_call_id


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _iter_schema_columns(schema: dict[str, Any], table_name: str | None) -> list[dict[str, Any]]:
    normalized_table_filter = _normalize_text(table_name)
    scoped_table = str(schema.get("table_name") or "").strip()
    scoped_columns = schema.get("columns")

    if isinstance(scoped_columns, list):
        if normalized_table_filter and _normalize_text(scoped_table) and _normalize_text(scoped_table) != normalized_table_filter:
            return []
        return [
            {
                "table_name": scoped_table,
                "name": str(col.get("name") or "").strip(),
                "dtype": str(col.get("dtype") or col.get("type") or "").strip(),
                "description": str(col.get("description") or "").strip(),
                "aliases": col.get("aliases") if isinstance(col.get("aliases"), list) else [],
            }
            for col in scoped_columns
            if isinstance(col, dict) and str(col.get("name") or "").strip()
        ]

    tables = schema.get("tables")
    if not isinstance(tables, list):
        return []

    normalized: list[dict[str, Any]] = []
    for table in tables:
        if not isinstance(table, dict):
            continue
        candidate_table = str(table.get("table_name") or "").strip()
        if normalized_table_filter and _normalize_text(candidate_table) != normalized_table_filter:
            continue
        raw_columns = table.get("columns")
        if not isinstance(raw_columns, list):
            continue
        for col in raw_columns:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name") or "").strip()
            if not name:
                continue
            normalized.append(
                {
                    "table_name": candidate_table,
                    "name": name,
                    "dtype": str(col.get("dtype") or col.get("type") or "").strip(),
                    "description": str(col.get("description") or "").strip(),
                    "aliases": col.get("aliases") if isinstance(col.get("aliases"), list) else [],
                }
            )
    return normalized


def _match_rank(column: dict[str, Any], normalized_query: str) -> int | None:
    name = _normalize_text(column.get("name"))
    aliases = [_normalize_text(alias) for alias in column.get("aliases", [])]
    description = _normalize_text(column.get("description"))

    if not normalized_query:
        return None
    if name == normalized_query:
        return 1
    if any(alias == normalized_query for alias in aliases):
        return 2
    if normalized_query in name:
        return 3
    if any(normalized_query in alias for alias in aliases):
        return 4
    if normalized_query in description:
        return 5
    return None


def _quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def _iter_db_columns(
    *,
    data_path: str | None,
    table_name: str | None,
    table_names: list[str] | None,
) -> list[dict[str, Any]]:
    if not data_path:
        return []

    requested_table = str(table_name or "").strip()
    normalized_tables: list[str] = []
    seen: set[str] = set()
    for item in table_names or []:
        candidate = str(item or "").strip()
        if not candidate:
            continue
        dedupe = candidate.lower()
        if dedupe in seen:
            continue
        seen.add(dedupe)
        normalized_tables.append(candidate)

    try:
        con = duckdb.connect(data_path, read_only=True)
    except Exception:
        return []

    try:
        if requested_table:
            candidate_tables = [requested_table]
        elif normalized_tables:
            candidate_tables = normalized_tables
        else:
            rows = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
            candidate_tables = [str(row[0]).strip() for row in rows if row and str(row[0]).strip()]

        columns: list[dict[str, Any]] = []
        for table in candidate_tables:
            try:
                describe_rows = con.execute(f"DESCRIBE {_quote_identifier(table)}").fetchall()
            except Exception:
                continue
            for row in describe_rows:
                if not row:
                    continue
                name = str(row[0] or "").strip()
                if not name:
                    continue
                columns.append(
                    {
                        "table_name": table,
                        "name": name,
                        "dtype": str(row[1] or "").strip() if len(row) > 1 else "",
                        "description": "",
                        "aliases": [],
                    }
                )
        return columns
    finally:
        con.close()


def search_schema(
    *,
    schema: dict[str, Any] | None = None,
    data_path: str | None = None,
    table_names: list[str] | None = None,
    query: str,
    table_name: str | None,
    max_results: int = 20,
    emit_tool_events: bool = True,
) -> dict[str, Any]:
    call_id = new_tool_call_id("search_schema") if emit_tool_events else ""
    normalized_query = _normalize_text(query)
    safe_max = max(1, min(100, int(max_results)))

    if emit_tool_events:
        emit_agent_event(
            "tool_call",
            {
                "tool": "search_schema",
                "args": {
                    "query": str(query or "").strip(),
                    "table_name": str(table_name or "").strip(),
                    "table_names": [str(item).strip() for item in (table_names or []) if str(item).strip()],
                    "max_results": safe_max,
                },
                "call_id": call_id,
            },
        )

    rows = _iter_schema_columns(schema if isinstance(schema, dict) else {}, table_name)
    if not rows:
        rows = _iter_db_columns(data_path=data_path, table_name=table_name, table_names=table_names)
    ranked: list[tuple[int, str, str, dict[str, Any]]] = []
    for column in rows:
        rank = _match_rank(column, normalized_query)
        if rank is None:
            continue
        ranked.append(
            (
                rank,
                _normalize_text(column.get("table_name")),
                _normalize_text(column.get("name")),
                {
                    "table_name": str(column.get("table_name") or "").strip(),
                    "name": str(column.get("name") or "").strip(),
                    "dtype": str(column.get("dtype") or "").strip(),
                    "description": str(column.get("description") or "").strip(),
                },
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, table_key, name_key, payload in ranked:
        dedupe_key = f"{table_key}:{name_key}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(payload)
        if len(deduped) >= safe_max:
            break

    output = {
        "query": str(query or "").strip(),
        "table_name": str(table_name or "").strip(),
        "match_count": len(deduped),
        "columns": deduped,
    }
    if emit_tool_events:
        emit_agent_event(
            "tool_result",
            {
                "call_id": call_id,
                "output": output,
                "status": "success",
                "duration_ms": 1,
            },
        )
    return output
