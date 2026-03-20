"""Chunked schema scanning tool for relevance-first enrichment."""

from __future__ import annotations

from typing import Any

from ..events import emit_agent_event
from . import new_tool_call_id


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _score_table_chunk(
    *,
    table: dict[str, Any],
    normalized_terms: list[str],
) -> tuple[int, list[dict[str, str]]]:
    table_name = str(table.get("table_name") or "").strip()
    table_context = _normalize_text(table.get("context"))
    columns_raw = table.get("columns")
    columns = columns_raw if isinstance(columns_raw, list) else []
    score = 0
    matched_columns: list[dict[str, str]] = []

    for column in columns:
        if not isinstance(column, dict):
            continue
        name = str(column.get("name") or "").strip()
        if not name:
            continue
        haystacks = [
            _normalize_text(name),
            _normalize_text(column.get("description")),
            _normalize_text(" ".join(str(alias or "") for alias in (column.get("aliases") or []))),
        ]
        local_hits = 0
        for term in normalized_terms:
            if any(term and term in hay for hay in haystacks):
                local_hits += 1
        if local_hits:
            score += local_hits * 3
            matched_columns.append(
                {
                    "table_name": table_name,
                    "name": name,
                    "dtype": str(column.get("dtype") or column.get("type") or "").strip(),
                    "description": str(column.get("description") or "").strip(),
                }
            )

    for term in normalized_terms:
        if term and term in _normalize_text(table_name):
            score += 2
        if term and term in table_context:
            score += 1

    return score, matched_columns


def scan_schema_chunks(
    *,
    schema: dict[str, Any] | None,
    query_terms: list[str],
    table_names: list[str] | None = None,
    chunk_size: int = 4,
    max_chunks: int = 12,
    emit_tool_events: bool = True,
) -> dict[str, Any]:
    call_id = new_tool_call_id("scan_schema_chunks") if emit_tool_events else ""
    normalized_terms = [_normalize_text(term) for term in (query_terms or []) if _normalize_text(term)]
    table_filter = {str(item or "").strip().lower() for item in (table_names or []) if str(item or "").strip()}
    safe_chunk_size = max(1, min(16, int(chunk_size or 4)))
    safe_max_chunks = max(1, min(40, int(max_chunks or 12)))

    if emit_tool_events:
        emit_agent_event(
            "tool_call",
            {
                "tool": "scan_schema_chunks",
                "args": {
                    "query_terms": [str(term) for term in query_terms or []],
                    "table_names": [str(item).strip() for item in (table_names or []) if str(item).strip()],
                    "chunk_size": safe_chunk_size,
                    "max_chunks": safe_max_chunks,
                },
                "call_id": call_id,
            },
        )

    tables = []
    if isinstance(schema, dict) and isinstance(schema.get("tables"), list):
        for table in schema.get("tables") or []:
            if not isinstance(table, dict):
                continue
            table_name = str(table.get("table_name") or "").strip()
            if not table_name:
                continue
            if table_filter and table_name.lower() not in table_filter:
                continue
            tables.append(table)

    scanned_chunks = 0
    relevant_tables: list[dict[str, Any]] = []
    discovered_columns: list[dict[str, str]] = []
    for idx in range(0, len(tables), safe_chunk_size):
        if scanned_chunks >= safe_max_chunks:
            break
        chunk = tables[idx : idx + safe_chunk_size]
        scanned_chunks += 1
        chunk_has_signal = False
        for table in chunk:
            score, matched = _score_table_chunk(table=table, normalized_terms=normalized_terms)
            if score <= 0:
                continue
            chunk_has_signal = True
            table_name = str(table.get("table_name") or "").strip()
            table_context = str(table.get("context") or "").strip()
            relevant_tables.append(
                {
                    "table_name": table_name,
                    "context": table_context,
                    "score": score,
                    "matched_columns": matched[:10],
                }
            )
            discovered_columns.extend(matched)
        if chunk_has_signal and len(relevant_tables) >= 6:
            break

    deduped_columns: list[dict[str, str]] = []
    seen_cols: set[str] = set()
    for item in discovered_columns:
        key = f"{str(item.get('table_name') or '').lower()}::{str(item.get('name') or '').lower()}"
        if key in seen_cols:
            continue
        seen_cols.add(key)
        deduped_columns.append(item)
        if len(deduped_columns) >= 80:
            break

    output = {
        "query_terms": [str(term) for term in query_terms or []],
        "chunks_scanned": scanned_chunks,
        "relevant_table_count": len(relevant_tables),
        "relevant_tables": relevant_tables,
        "columns": deduped_columns,
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
