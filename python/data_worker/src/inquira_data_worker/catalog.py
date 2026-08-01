"""Atomic DuckDB workspace catalogs over immutable Parquet snapshots."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
import math
from pathlib import Path
from typing import Any
from uuid import UUID

import duckdb

from .adapters.file import _sql_string
from .errors import AdapterError


@dataclass(frozen=True)
class CatalogBuild:
    database_path: str
    fingerprint: str
    changed: bool
    table_count: int
    byte_size: int


@dataclass(frozen=True)
class CatalogPreview:
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    mode: str
    offset: int
    limit: int


def _identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _existing_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        connection = duckdb.connect(str(path), read_only=True)
        try:
            row = connection.execute("SELECT fingerprint FROM inquira_internal.catalog_metadata LIMIT 1").fetchone()
            return str(row[0]) if row else ""
        finally:
            connection.close()
    except Exception:
        return ""


def _preview_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, time, UUID)):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return str(value)


def preview_catalog(params: dict[str, Any]) -> CatalogPreview:
    database_value = params.get("database_path")
    table_name = str(params.get("table_name") or "").strip()
    mode = str(params.get("mode") or "head").strip().lower()
    limit = params.get("limit", 100)
    if (
        not isinstance(database_value, str)
        or not database_value.strip()
        or not table_name
        or mode not in {"head", "tail"}
        or not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
        or limit > 100
    ):
        raise AdapterError(
            "invalid_params",
            "database_path, table_name, head or tail mode, and a limit from 1 to 100 are required.",
        )
    database = Path(database_value).expanduser()
    if not database.is_absolute() or database.suffix.lower() != ".duckdb" or not database.is_file():
        raise AdapterError("catalog_path_invalid", "Workspace catalog does not exist.")
    connection = duckdb.connect(str(database.resolve(strict=True)), read_only=True)
    try:
        registered = connection.execute(
            "SELECT 1 FROM inquira_internal.catalog_tables WHERE name = ? LIMIT 1",
            [table_name],
        ).fetchone()
        if registered is None:
            raise AdapterError("dataset_not_found", "Dataset was not found in this workspace catalog.")
        row_count = int(connection.execute(f"SELECT COUNT(*) FROM {_identifier(table_name)}").fetchone()[0])
        offset = max(row_count - limit, 0) if mode == "tail" else 0
        cursor = connection.execute(
            f"SELECT * FROM {_identifier(table_name)} LIMIT ? OFFSET ?", [limit, offset]
        )
        columns = [str(item[0]) for item in cursor.description]
        rows = [
            {column: _preview_value(value) for column, value in zip(columns, values, strict=True)}
            for values in cursor.fetchall()
        ]
        return CatalogPreview(table_name, columns, rows, row_count, mode, offset, limit)
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError("catalog_preview_failed", f"Could not preview workspace dataset: {exc}") from exc
    finally:
        connection.close()


def build_catalog(params: dict[str, Any]) -> CatalogBuild:
    database_value = params.get("database_path")
    fingerprint = str(params.get("fingerprint") or "").strip()
    tables = params.get("tables")
    if not isinstance(database_value, str) or not database_value.strip() or not fingerprint or not isinstance(tables, list):
        raise AdapterError("invalid_params", "database_path, fingerprint, and tables are required.")
    database = Path(database_value).expanduser().resolve()
    normalized: list[tuple[str, str, Path]] = []
    names: set[str] = set()
    for item in tables:
        if not isinstance(item, dict):
            raise AdapterError("invalid_params", "Catalog tables must be objects.")
        table_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        snapshot_value = item.get("snapshot_path")
        if not table_id or not name or not isinstance(snapshot_value, str) or not snapshot_value.strip():
            raise AdapterError("invalid_params", "Every catalog table requires an id, name, and snapshot_path.")
        if name.casefold() in names:
            raise AdapterError("catalog_name_duplicate", "Catalog table names must be unique.")
        names.add(name.casefold())
        snapshot = Path(snapshot_value).expanduser()
        if snapshot.suffix.lower() != ".parquet":
            raise AdapterError("catalog_snapshot_invalid", "Catalog snapshots must be Parquet files.")
        if not snapshot.exists() or not snapshot.is_file():
            raise AdapterError("catalog_snapshot_missing", f"Snapshot does not exist: {snapshot}")
        normalized.append((table_id, name, snapshot.resolve(strict=True)))

    if _existing_fingerprint(database) == fingerprint:
        return CatalogBuild(str(database), fingerprint, False, len(normalized), database.stat().st_size)

    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_name(f".{database.name}.{uuid.uuid4().hex}.tmp")
    try:
        connection = duckdb.connect(str(temporary))
        try:
            connection.execute("CREATE SCHEMA inquira_internal")
            connection.execute("CREATE TABLE inquira_internal.catalog_metadata(fingerprint VARCHAR NOT NULL)")
            connection.execute("INSERT INTO inquira_internal.catalog_metadata VALUES (?)", [fingerprint])
            connection.execute("CREATE TABLE inquira_internal.catalog_tables(id VARCHAR NOT NULL, name VARCHAR NOT NULL, snapshot_path VARCHAR NOT NULL)")
            for table_id, name, snapshot in normalized:
                connection.execute("INSERT INTO inquira_internal.catalog_tables VALUES (?, ?, ?)", [table_id, name, str(snapshot)])
                connection.execute(
                    f"CREATE VIEW {_identifier(name)} AS SELECT * FROM read_parquet({_sql_string(snapshot)})"
                )
            connection.execute("CHECKPOINT")
        finally:
            connection.close()
        os.chmod(temporary, 0o600)
        os.replace(temporary, database)
    except AdapterError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise AdapterError("catalog_build_failed", f"Could not build workspace catalog: {exc}") from exc
    return CatalogBuild(str(database), fingerprint, True, len(normalized), database.stat().st_size)
