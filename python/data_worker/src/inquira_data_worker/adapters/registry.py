"""Adapter registry used by RPC dispatch."""

from __future__ import annotations

from ..errors import AdapterError
from .excel import ExcelAdapter
from .file import CSVAdapter, FileAdapter, JSONAdapter, ParquetAdapter
from .sqlite import SQLiteAdapter


def get_adapter(kind: str) -> FileAdapter | ExcelAdapter | SQLiteAdapter:
    normalized = str(kind or "").strip().lower()
    if normalized == "csv":
        return CSVAdapter()
    if normalized == "parquet":
        return ParquetAdapter()
    if normalized == "excel":
        return ExcelAdapter()
    if normalized == "json":
        return JSONAdapter()
    if normalized == "sqlite":
        return SQLiteAdapter()
    raise AdapterError("adapter_not_supported", f"Adapter {normalized or '(empty)'} is not supported yet.")
