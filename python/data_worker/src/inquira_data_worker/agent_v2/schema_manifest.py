"""Schema manifest and context-pack helpers for agent v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def estimate_tokens(value: Any) -> int:
    """Cheap conservative token estimate used for schema budgeting."""
    if value is None:
        return 0
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            text = str(value)
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return 0
    return max(1, (len(normalized) + 3) // 4)


def schema_context_budget(context_window: Any) -> int:
    try:
        parsed = int(context_window or 0)
    except (TypeError, ValueError):
        parsed = 0
    if parsed <= 0:
        return 10_000
    return min(10_000, max(3_000, int(parsed * 0.10)))


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _schema_tables(workspace_schema: dict[str, Any]) -> list[dict[str, Any]]:
    tables = workspace_schema.get("tables")
    if isinstance(tables, list):
        return [item for item in tables if isinstance(item, dict)]
    table_name = _as_text(workspace_schema.get("table_name"))
    if table_name:
        return [workspace_schema]
    return []


def _compact_column(column: dict[str, Any]) -> dict[str, Any]:
    aliases = [_as_text(item) for item in _as_list(column.get("aliases")) if _as_text(item)]
    return {
        "name": _as_text(column.get("name")),
        "dtype": _as_text(column.get("dtype") or column.get("type")),
        "aliases": aliases,
    }


def _full_column(column: dict[str, Any]) -> dict[str, Any]:
    payload = _compact_column(column)
    payload["description"] = _as_text(column.get("description"))
    samples = column.get("samples")
    if samples is None:
        samples = column.get("sample_values")
    if isinstance(samples, list):
        payload["sample_values"] = samples[:8]
    else:
        payload["sample_values"] = []
    return payload


def build_schema_manifest(
    *,
    workspace_schema: dict[str, Any] | None,
    data_path: str | None = None,
) -> dict[str, Any]:
    schema = workspace_schema if isinstance(workspace_schema, dict) else {}
    schema_folder_path = _as_text(schema.get("schema_folder_path"))
    if not schema_folder_path and data_path:
        schema_folder_path = str(Path(data_path).expanduser().parent / "meta")

    table_payloads: list[dict[str, Any]] = []
    for table in _schema_tables(schema):
        table_name = _as_text(table.get("table_name"))
        if not table_name:
            continue
        columns = []
        for column in _as_list(table.get("columns")):
            if not isinstance(column, dict) or not _as_text(column.get("name")):
                continue
            compact = _compact_column(column)
            full = _full_column(column)
            columns.append(
                {
                    **full,
                    "token_count_compact": estimate_tokens(compact),
                    "token_count_full": estimate_tokens(full),
                }
            )

        compact_table = {
            "table_name": table_name,
            "description": _as_text(table.get("context") or table.get("description")),
            "columns": [
                {
                    "name": item["name"],
                    "dtype": item["dtype"],
                    "aliases": item.get("aliases", []),
                }
                for item in columns
            ],
        }
        full_table = {
            "table_name": table_name,
            "description": _as_text(table.get("context") or table.get("description")),
            "columns": [
                {
                    "name": item["name"],
                    "dtype": item["dtype"],
                    "aliases": item.get("aliases", []),
                    "description": item.get("description", ""),
                    "sample_values": item.get("sample_values", []),
                }
                for item in columns
            ],
        }
        table_payloads.append(
            {
                **full_table,
                "token_count_compact": estimate_tokens(compact_table),
                "token_count_full": estimate_tokens(full_table),
                "columns": columns,
            }
        )

    compact_total = estimate_tokens(
        [
            {
                "table_name": table["table_name"],
                "description": table.get("description", ""),
                "columns": [
                    {
                        "name": column["name"],
                        "dtype": column["dtype"],
                        "aliases": column.get("aliases", []),
                    }
                    for column in table.get("columns", [])
                ],
            }
            for table in table_payloads
        ]
    )
    full_total = estimate_tokens(table_payloads)
    return {
        "schema_version": _as_text(schema.get("schema_version")) or _as_text(schema.get("version")) or "v1",
        "schema_folder_path": schema_folder_path,
        "table_count": len(table_payloads),
        "token_count_compact": compact_total,
        "token_count_full": full_total,
        "tables": table_payloads,
    }


def _compact_table(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "table_name": table.get("table_name", ""),
        "description": table.get("description", ""),
        "columns": [
            {
                "name": column.get("name", ""),
                "dtype": column.get("dtype", ""),
                "aliases": column.get("aliases", []),
            }
            for column in _as_list(table.get("columns"))
        ],
    }


def _full_table(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "table_name": table.get("table_name", ""),
        "description": table.get("description", ""),
        "columns": [
            {
                "name": column.get("name", ""),
                "dtype": column.get("dtype", ""),
                "aliases": column.get("aliases", []),
                "description": column.get("description", ""),
                "sample_values": column.get("sample_values", []),
            }
            for column in _as_list(table.get("columns"))
        ],
    }


def build_schema_context_pack(
    *,
    manifest: dict[str, Any],
    context_window: Any,
) -> dict[str, Any]:
    budget = schema_context_budget(context_window)
    full_tokens = int(manifest.get("token_count_full") or 0)
    compact_tokens = int(manifest.get("token_count_compact") or 0)
    tables = [table for table in _as_list(manifest.get("tables")) if isinstance(table, dict)]

    if full_tokens and full_tokens <= budget:
        return {
            "mode": "full",
            "budget_tokens": budget,
            "estimated_tokens": full_tokens,
            "schema_version": manifest.get("schema_version", "v1"),
            "schema_folder_path": manifest.get("schema_folder_path", ""),
            "tables": [_full_table(table) for table in tables],
            "omitted": [],
        }

    selected: list[dict[str, Any]] = []
    used = 0
    omitted: list[str] = []
    for table in tables:
        compact = _compact_table(table)
        table_tokens = estimate_tokens(compact)
        if selected and used + table_tokens > budget:
            omitted.append(str(table.get("table_name") or ""))
            continue
        selected.append(compact)
        used += table_tokens

    return {
        "mode": "compact",
        "budget_tokens": budget,
        "estimated_tokens": used or compact_tokens,
        "schema_version": manifest.get("schema_version", "v1"),
        "schema_folder_path": manifest.get("schema_folder_path", ""),
        "tables": selected,
        "omitted": {
            "tables": [item for item in omitted if item],
            "fields": ["column.description", "column.sample_values"],
        },
    }
