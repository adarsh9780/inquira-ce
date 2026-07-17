"""Adapter registry used by RPC dispatch."""

from __future__ import annotations

from ..errors import AdapterError
from .file import CSVAdapter, FileAdapter, ParquetAdapter


def get_adapter(kind: str) -> FileAdapter:
    normalized = str(kind or "").strip().lower()
    if normalized == "csv":
        return CSVAdapter()
    if normalized == "parquet":
        return ParquetAdapter()
    raise AdapterError("adapter_not_supported", f"Adapter {normalized or '(empty)'} is not supported yet.")
