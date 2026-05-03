"""Conversation-scoped schema memory helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SchemaMemoryService:
    """Build and merge compact schema memory snapshots."""

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item or "").strip() for item in value if str(item or "").strip()]

    @staticmethod
    def _workspace_tables(workspace_schema: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(workspace_schema, dict):
            return []
        raw_tables = workspace_schema.get("tables")
        if isinstance(raw_tables, list):
            return [item for item in raw_tables if isinstance(item, dict)]
        table_name = str(workspace_schema.get("table_name") or "").strip()
        columns = workspace_schema.get("columns")
        if table_name:
            return [
                {
                    "table_name": table_name,
                    "context": str(workspace_schema.get("context") or ""),
                    "columns": columns if isinstance(columns, list) else [],
                }
            ]
        return []

    @staticmethod
    def _data_fingerprint(data_path: str | None) -> str:
        raw = str(data_path or "").strip()
        if not raw:
            return ""
        try:
            mtime_ns = Path(raw).expanduser().stat().st_mtime_ns
        except OSError:
            return raw
        return f"{raw}:{mtime_ns}"

    @staticmethod
    def build_turn_schema_usage(
        *,
        workspace_schema: dict[str, Any] | None,
        data_path: str | None,
    ) -> dict[str, Any]:
        """Extract the compact schema snapshot used for one turn."""
        tables_loaded: list[str] = []
        columns_loaded: dict[str, list[str]] = {}
        notes: list[str] = []
        for table in SchemaMemoryService._workspace_tables(workspace_schema):
            table_name = str(table.get("table_name") or "").strip()
            if not table_name:
                continue
            tables_loaded.append(table_name)
            column_names: list[str] = []
            raw_columns = table.get("columns")
            for column in raw_columns if isinstance(raw_columns, list) else []:
                if not isinstance(column, dict):
                    continue
                name = str(column.get("name") or "").strip()
                if not name:
                    continue
                column_names.append(name)
                description = str(column.get("description") or "").strip()
                if description and len(notes) < 10:
                    notes.append(f"{table_name}.{name}: {description}")
            columns_loaded[table_name] = column_names
            context = str(table.get("context") or "").strip()
            if context and len(notes) < 10:
                notes.append(f"{table_name}: {context}")

        return {
            "schema_version": 1,
            "data_fingerprint": SchemaMemoryService._data_fingerprint(data_path),
            "tables_loaded": tables_loaded,
            "columns_loaded": columns_loaded,
            "join_paths": [],
            "important_notes": notes,
            "token_estimate": sum(len(name) for name in tables_loaded) + sum(
                len(name)
                for column_names in columns_loaded.values()
                for name in column_names
            ),
        }

    @staticmethod
    def merge_conversation_schema_memory(
        current_memory_json: str | None,
        current_version: int | None,
        turn_usage: dict[str, Any],
    ) -> tuple[str, int]:
        """Merge one turn's schema usage into the conversation-level memory."""
        try:
            current = json.loads(str(current_memory_json or "") or "{}")
        except json.JSONDecodeError:
            current = {}
        if not isinstance(current, dict):
            current = {}

        merged_tables: list[str] = []
        seen_tables: set[str] = set()
        for table_name in (
            SchemaMemoryService._string_list(current.get("tables_loaded"))
            + SchemaMemoryService._string_list(turn_usage.get("tables_loaded"))
        ):
            candidate = str(table_name or "").strip()
            if not candidate or candidate.lower() in seen_tables:
                continue
            seen_tables.add(candidate.lower())
            merged_tables.append(candidate)

        merged_columns: dict[str, list[str]] = {}
        raw_columns = current.get("columns_loaded") if isinstance(current.get("columns_loaded"), dict) else {}
        raw_turn_columns = (
            turn_usage.get("columns_loaded") if isinstance(turn_usage.get("columns_loaded"), dict) else {}
        )
        for table_name in merged_tables:
            names: list[str] = []
            seen_names: set[str] = set()
            for source in (raw_columns.get(table_name) or [], raw_turn_columns.get(table_name) or []):
                for name in source if isinstance(source, list) else []:
                    candidate = str(name or "").strip()
                    if not candidate or candidate.lower() in seen_names:
                        continue
                    seen_names.add(candidate.lower())
                    names.append(candidate)
            merged_columns[table_name] = names

        merged_notes: list[str] = []
        seen_notes: set[str] = set()
        for note in (
            SchemaMemoryService._string_list(current.get("important_notes"))
            + SchemaMemoryService._string_list(turn_usage.get("important_notes"))
        ):
            candidate = str(note or "").strip()
            if not candidate or candidate.lower() in seen_notes:
                continue
            seen_notes.add(candidate.lower())
            merged_notes.append(candidate)
            if len(merged_notes) >= 20:
                break

        current_join_paths = SchemaMemoryService._string_list(current.get("join_paths"))
        turn_join_paths = SchemaMemoryService._string_list(turn_usage.get("join_paths"))

        merged: dict[str, Any] = {
            "schema_version": int(turn_usage.get("schema_version") or current.get("schema_version") or 1),
            "data_fingerprint": str(turn_usage.get("data_fingerprint") or current.get("data_fingerprint") or ""),
            "tables_loaded": merged_tables,
            "columns_loaded": merged_columns,
            "join_paths": current_join_paths or turn_join_paths,
            "important_notes": merged_notes,
            "token_estimate": int(current.get("token_estimate") or 0) + int(turn_usage.get("token_estimate") or 0),
        }
        return json.dumps(merged), int(current_version or 0) + 1
