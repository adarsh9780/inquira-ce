"""Schema retrieval tool for agent v2."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import time
from typing import Any

import duckdb

from ..events import emit_agent_event
from . import new_tool_call_id


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _normalize_queries(
    *,
    query: str | None,
    queries: list[str] | None,
    max_items: int = 12,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    combined: list[str] = []
    if isinstance(query, str) and str(query).strip():
        combined.append(str(query).strip())
    if isinstance(queries, list):
        combined.extend(str(item).strip() for item in queries if str(item).strip())

    for candidate in combined:
        token = _normalize_text(candidate)
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
        if len(normalized) >= max(1, int(max_items)):
            break
    return normalized


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
    query_tokens = [token for token in normalized_query.split(" ") if token]

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
    if query_tokens and len(query_tokens) > 1 and all(token in name for token in query_tokens):
        return 4
    if normalized_query in description:
        return 5
    if query_tokens and len(query_tokens) > 1 and all(token in description for token in query_tokens):
        return 6
    return None


def _best_match_rank(
    *,
    column: dict[str, Any],
    normalized_queries: list[str],
) -> tuple[int, list[str]] | None:
    best_rank: int | None = None
    matched_queries: list[str] = []
    for normalized_query in normalized_queries:
        rank = _match_rank(column, normalized_query)
        if rank is None:
            continue
        matched_queries.append(normalized_query)
        if best_rank is None or rank < best_rank:
            best_rank = rank
    if best_rank is None:
        return None
    return best_rank, matched_queries


def _quote_identifier(identifier: str) -> str:
    return f'"{identifier.replace(chr(34), chr(34) * 2)}"'


def _workspace_db_mtime_ns(data_path: str | None) -> int:
    if not data_path:
        return 0
    try:
        return int(Path(data_path).stat().st_mtime_ns)
    except Exception:
        return 0


@lru_cache(maxsize=256)
def _cached_db_columns(
    *,
    data_path: str,
    requested_table: str,
    scoped_tables: tuple[str, ...],
    mtime_ns: int,
) -> tuple[tuple[str, str, str], ...]:
    _ = mtime_ns
    try:
        con = duckdb.connect(data_path, read_only=True)
    except Exception:
        return tuple()

    try:
        if requested_table:
            candidate_tables = [requested_table]
        elif scoped_tables:
            candidate_tables = list(scoped_tables)
        else:
            rows = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
            candidate_tables = [str(row[0]).strip() for row in rows if row and str(row[0]).strip()]

        columns: list[tuple[str, str, str]] = []
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
                dtype = str(row[1] or "").strip() if len(row) > 1 else ""
                columns.append((str(table).strip(), name, dtype))
        return tuple(columns)
    finally:
        con.close()


def _iter_db_columns(
    *,
    data_path: str | None,
    table_name: str | None,
    table_names: list[str] | None,
) -> list[dict[str, Any]]:
    if not data_path:
        return []

    db_path = str(data_path or "").strip()
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

    rows = _cached_db_columns(
        data_path=db_path,
        requested_table=requested_table,
        scoped_tables=tuple(normalized_tables),
        mtime_ns=_workspace_db_mtime_ns(db_path),
    )
    return [
        {
            "table_name": table,
            "name": name,
            "dtype": dtype,
            "description": "",
            "aliases": [],
        }
        for table, name, dtype in rows
    ]


def search_schema(
    *,
    schema: dict[str, Any] | None = None,
    data_path: str | None = None,
    table_names: list[str] | None = None,
    query: str,
    queries: list[str] | None = None,
    table_name: str | None,
    max_results: int = 20,
    limit_per_query: int | None = None,
    explanation: str = "",
    emit_tool_events: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    call_id = new_tool_call_id("search_schema") if emit_tool_events else ""
    normalized_queries = _normalize_queries(query=query, queries=queries, max_items=12)
    safe_max = max(1, min(100, int(max_results)))
    safe_per_query = max(1, min(50, int(limit_per_query or max_results or 20)))

    if emit_tool_events:
        emit_agent_event(
            "tool_call",
            {
                "tool": "search_schema",
                "args": {
                    "query": str(query or "").strip(),
                    "queries": [str(item).strip() for item in (queries or []) if str(item).strip()],
                    "table_name": str(table_name or "").strip(),
                    "table_names": [str(item).strip() for item in (table_names or []) if str(item).strip()],
                    "max_results": safe_max,
                    "limit_per_query": safe_per_query,
                    "explanation": str(explanation or "").strip(),
                },
                "call_id": call_id,
                "explanation": str(explanation or "").strip(),
            },
        )

    rows = _iter_schema_columns(schema if isinstance(schema, dict) else {}, table_name)
    if not rows:
        rows = _iter_db_columns(data_path=data_path, table_name=table_name, table_names=table_names)
    ranked: list[tuple[int, int, str, str, dict[str, Any]]] = []
    results_by_query: dict[str, list[dict[str, Any]]] = {item: [] for item in normalized_queries}
    for column in rows:
        matched = _best_match_rank(column=column, normalized_queries=normalized_queries)
        if matched is None:
            continue
        rank, matched_queries = matched
        column_payload = {
            "table_name": str(column.get("table_name") or "").strip(),
            "name": str(column.get("name") or "").strip(),
            "dtype": str(column.get("dtype") or "").strip(),
            "description": str(column.get("description") or "").strip(),
        }
        for query_value in matched_queries:
            query_rank = _match_rank(column, query_value)
            if query_rank is None:
                continue
            bucket = results_by_query.setdefault(query_value, [])
            bucket.append(
                {
                    **column_payload,
                    "matched_queries": [query_value],
                    "rank": query_rank,
                }
            )
        ranked.append(
            (
                rank,
                -len(matched_queries),
                _normalize_text(column.get("table_name")),
                _normalize_text(column.get("name")),
                {**column_payload, "matched_queries": matched_queries},
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    for query_value, bucket in list(results_by_query.items()):
        bucket.sort(
            key=lambda item: (
                int(item.get("rank") or 999),
                _normalize_text(item.get("table_name")),
                _normalize_text(item.get("name")),
            )
        )
        deduped_bucket: list[dict[str, Any]] = []
        seen_bucket: set[str] = set()
        for item in bucket:
            key = f"{_normalize_text(item.get('table_name'))}:{_normalize_text(item.get('name'))}"
            if key in seen_bucket:
                continue
            seen_bucket.add(key)
            clean = dict(item)
            clean.pop("rank", None)
            deduped_bucket.append(clean)
            if len(deduped_bucket) >= safe_per_query:
                break
        results_by_query[query_value] = deduped_bucket

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, _, table_key, name_key, payload in ranked:
        dedupe_key = f"{table_key}:{name_key}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(payload)
        if len(deduped) >= safe_max:
            break
    matched_queries = {
        str(query_value).strip().lower()
        for row in deduped
        for query_value in (row.get("matched_queries") or [])
        if str(query_value).strip()
    }
    covered_queries = [item for item in normalized_queries if item.lower() in matched_queries]
    missing_queries = [item for item in normalized_queries if item.lower() not in matched_queries]

    output = {
        "query": str(query or "").strip(),
        "queries": normalized_queries,
        "covered_queries": covered_queries,
        "missing_queries": missing_queries,
        "unmatched_queries": missing_queries,
        "table_name": str(table_name or "").strip(),
        "match_count": len(deduped),
        "columns": deduped,
        "results_by_query": results_by_query,
        "merged_ranked_results": deduped,
    }
    if emit_tool_events:
        emit_agent_event(
            "tool_result",
            {
                "call_id": call_id,
                "output": output,
                "status": "success",
                "duration_ms": max(1, int((time.perf_counter() - started) * 1000)),
            },
        )
    return output
