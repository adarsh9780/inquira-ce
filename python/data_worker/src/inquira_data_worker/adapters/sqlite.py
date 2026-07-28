"""Read-only SQLite adapter with canonical Parquet materialization."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import duckdb

from ..errors import AdapterError
from ..models import (
    AdapterRequest,
    Column,
    Discovery,
    Materialization,
    MaterializedOutput,
    MaterializeRequest,
    Preview,
    SourceObject,
)
from .file import MAX_PREVIEW_ROWS, _json_value, _sql_string

INSERT_BATCH_SIZE = 1000
OBJECT_KINDS = {"table", "view"}
SQLITE_SUFFIXES = {".sqlite", ".sqlite3", ".db"}


@dataclass(frozen=True)
class _SQLiteObject:
    object_id: str
    name: str
    kind: str


@dataclass(frozen=True)
class _ObjectAnalysis:
    columns: list[Column]
    row_count: int


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _object_id(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _unique_names(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    used: dict[str, int] = {}
    for index, value in enumerate(values):
        base = str(value or "").strip() or f"column_{index + 1}"
        key = base.casefold()
        count = used.get(key, 0) + 1
        used[key] = count
        result.append(base if count == 1 else f"{base}_{count}")
    return result


def _runtime_type(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int) and -(2**63) <= value < 2**63:
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    if isinstance(value, bytes):
        return "BLOB"
    return "VARCHAR"


def _declared_type(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if "INT" in normalized:
        return "BIGINT"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE"
    if "BLOB" in normalized:
        return "BLOB"
    if "BOOL" in normalized:
        return "BOOLEAN"
    return "VARCHAR"


def _merge_type(current: str | None, incoming: str | None) -> str | None:
    if incoming is None:
        return current
    if current is None or current == incoming:
        return incoming
    if {current, incoming} <= {"BIGINT", "DOUBLE"}:
        return "DOUBLE"
    return "VARCHAR"


def _convert(value: Any, data_type: str) -> Any:
    if value is None:
        return None
    if data_type == "VARCHAR":
        normalized = _json_value(value)
        return normalized if isinstance(normalized, str) else str(normalized)
    if data_type == "DOUBLE" and isinstance(value, int):
        return float(value)
    return value


class SQLiteAdapter:
    kind = "sqlite"

    def _source(self, value: str) -> Path:
        if not str(value or "").strip():
            raise AdapterError("invalid_params", "A source path is required.")
        raw = Path(value).expanduser()
        if not raw.exists():
            raise AdapterError("source_not_found", f"Source file does not exist: {raw}")
        if not raw.is_file():
            raise AdapterError("source_not_file", "Source path must be a regular file.")
        if raw.suffix.lower() not in SQLITE_SUFFIXES:
            raise AdapterError(
                "source_extension_mismatch",
                "Expected a .sqlite, .sqlite3, or .db file extension.",
            )
        if raw.stat().st_size == 0:
            raise AdapterError("source_unreadable", "Could not read sqlite source: file is empty.")
        return raw.resolve(strict=True)

    def _fingerprint(self, path: Path) -> str:
        digest = hashlib.sha256()
        for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-journal")):
            if not candidate.exists():
                continue
            digest.update(candidate.name.encode("utf-8"))
            digest.update(b"\0")
            try:
                with candidate.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        digest.update(chunk)
            except FileNotFoundError:
                digest.update(b"<changed-during-fingerprint>")
        return "sha256:" + digest.hexdigest()

    def _open(self, path: Path) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=5)
            connection.enable_load_extension(False)
            connection.execute("PRAGMA query_only = ON")
            connection.execute("PRAGMA trusted_schema = OFF")
            connection.execute("PRAGMA busy_timeout = 5000")
            return connection
        except Exception as exc:
            raise AdapterError("source_unreadable", f"Could not read sqlite source: {exc}") from exc

    def _objects(self, connection: sqlite3.Connection) -> list[_SQLiteObject]:
        try:
            rows = connection.execute(
                """
                SELECT type, name
                FROM sqlite_schema
                WHERE type IN ('table', 'view')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name COLLATE NOCASE, name
                """
            ).fetchall()
        except Exception as exc:
            raise AdapterError("source_unreadable", f"Could not inspect sqlite source: {exc}") from exc
        return [
            _SQLiteObject(object_id=_object_id(str(kind), str(name)), name=str(name), kind=str(kind))
            for kind, name in rows
        ]

    def _resolve_object(self, objects: list[_SQLiteObject], object_id: str) -> _SQLiteObject:
        normalized = str(object_id or "")
        for item in objects:
            if item.object_id == normalized:
                return item
        raise AdapterError("source_selection_missing", "The selected SQLite table or view no longer exists.")

    def _declared_types(
        self,
        connection: sqlite3.Connection,
        source: _SQLiteObject,
        width: int,
    ) -> list[str]:
        try:
            rows = connection.execute(f"PRAGMA table_xinfo({_quote_identifier(source.name)})").fetchall()
        except Exception:
            rows = []
        visible = [row for row in rows if len(row) < 7 or int(row[6] or 0) != 1]
        values = [_declared_type(str(row[2] or "")) for row in visible[:width]]
        return values + ["VARCHAR"] * max(0, width - len(values))

    def _analyse(
        self,
        connection: sqlite3.Connection,
        source: _SQLiteObject,
        limit: int | None,
    ) -> _ObjectAnalysis:
        query = f"SELECT * FROM {_quote_identifier(source.name)}"
        if limit is not None:
            query += f" LIMIT {max(0, int(limit))}"
        try:
            cursor = connection.execute(query)
            names = _unique_names(item[0] for item in (cursor.description or []))
            if not names:
                raise AdapterError("source_unreadable", f"SQLite {source.kind} {source.name} has no columns.")
            inferred: list[str | None] = [None] * len(names)
            row_count = 0
            while rows := cursor.fetchmany(INSERT_BATCH_SIZE):
                for row in rows:
                    for index, value in enumerate(row):
                        inferred[index] = _merge_type(inferred[index], _runtime_type(value))
                row_count += len(rows)
            fallback = self._declared_types(connection, source, len(names))
            columns = [
                Column(name=name, data_type=inferred[index] or fallback[index])
                for index, name in enumerate(names)
            ]
            return _ObjectAnalysis(columns=columns, row_count=row_count)
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError(
                "source_unreadable",
                f"Could not read SQLite {source.kind} {source.name}: {exc}",
            ) from exc

    def discover(self, request: AdapterRequest) -> Discovery:
        path = self._source(request.source_path)
        before = self._fingerprint(path)
        connection = self._open(path)
        try:
            objects = self._objects(connection)
            discovered = []
            for source in objects:
                analysis = self._analyse(connection, source, 0)
                discovered.append(SourceObject(
                    id=source.object_id,
                    name=source.name,
                    kind=source.kind,
                    columns=analysis.columns,
                    metadata={
                        "column_count": len(analysis.columns),
                        "selectable": True,
                    },
                ))
        finally:
            connection.close()
        after = self._fingerprint(path)
        if after != before:
            raise AdapterError("source_changed", "SQLite source changed during discovery; inspect it again.")
        return Discovery(
            adapter_kind=self.kind,
            source_path=str(path),
            fingerprint=after,
            objects=discovered,
        )

    def preview(self, request: AdapterRequest, limit: int) -> Preview:
        if limit < 1 or limit > MAX_PREVIEW_ROWS:
            raise AdapterError("invalid_preview_limit", f"Preview limit must be between 1 and {MAX_PREVIEW_ROWS}.")
        path = self._source(request.source_path)
        connection = self._open(path)
        try:
            source = self._resolve_object(self._objects(connection), request.source_object_id)
            analysis = self._analyse(connection, source, limit + 1)
            cursor = connection.execute(
                f"SELECT * FROM {_quote_identifier(source.name)} LIMIT {limit + 1}"
            )
            raw_rows = cursor.fetchall()
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError("source_unreadable", f"Could not preview sqlite source: {exc}") from exc
        finally:
            connection.close()
        names = [column.name for column in analysis.columns]
        return Preview(
            columns=analysis.columns,
            rows=[
                {name: _json_value(value) for name, value in zip(names, row, strict=True)}
                for row in raw_rows[:limit]
            ],
            truncated=len(raw_rows) > limit,
        )

    def materialize(self, request: MaterializeRequest) -> Materialization:
        selected = request.selected_object_ids
        if not selected:
            raise AdapterError("source_selection_required", "Select at least one SQLite table or view.")
        if len(set(selected)) != len(selected):
            raise AdapterError("invalid_selection", "Selected SQLite objects must be unique.")
        path = self._source(request.source_path)
        target = Path(request.target_dir).expanduser().resolve()
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            raise AdapterError("target_not_empty", "Materialization target must be empty.")

        before = self._fingerprint(path)
        connection = self._open(path)
        outputs: list[MaterializedOutput] = []
        try:
            connection.execute("BEGIN")
            objects = self._objects(connection)
            sources = [self._resolve_object(objects, item) for item in selected]
            analyses = [self._analyse(connection, item, None) for item in sources]
            target.mkdir(parents=True, exist_ok=True)
            for index, (source, analysis) in enumerate(zip(sources, analyses, strict=True)):
                digest = hashlib.sha256(source.object_id.encode("utf-8")).hexdigest()[:12]
                relative_path = f"sqlite-{index + 1}-{digest}.parquet"
                output = target / relative_path
                self._write_object(connection, source, analysis, output)
                outputs.append(MaterializedOutput(
                    source_object_id=source.object_id,
                    name=source.name,
                    relative_path=relative_path,
                    format="parquet",
                    columns=analysis.columns,
                    row_count=analysis.row_count,
                    byte_size=output.stat().st_size,
                ))
            connection.rollback()
        except AdapterError:
            shutil.rmtree(target, ignore_errors=True)
            raise
        except Exception as exc:
            shutil.rmtree(target, ignore_errors=True)
            raise AdapterError("materialization_failed", f"Could not materialize sqlite source: {exc}") from exc
        finally:
            connection.close()

        after = self._fingerprint(path)
        if after != before:
            shutil.rmtree(target, ignore_errors=True)
            raise AdapterError("source_changed", "SQLite source changed during materialization; refresh again.")
        return Materialization(fingerprint=after, outputs=outputs)

    def _write_object(
        self,
        connection: sqlite3.Connection,
        source: _SQLiteObject,
        analysis: _ObjectAnalysis,
        output: Path,
    ) -> None:
        database = duckdb.connect()
        try:
            definitions = ", ".join(
                f"{_quote_identifier(column.name)} {column.data_type}" for column in analysis.columns
            )
            database.execute(f"CREATE TABLE snapshot_data ({definitions})")
            placeholders = ", ".join("?" for _ in analysis.columns)
            cursor = connection.execute(f"SELECT * FROM {_quote_identifier(source.name)}")
            while rows := cursor.fetchmany(INSERT_BATCH_SIZE):
                converted = [
                    [
                        _convert(value, column.data_type)
                        for value, column in zip(row, analysis.columns, strict=True)
                    ]
                    for row in rows
                ]
                database.executemany(f"INSERT INTO snapshot_data VALUES ({placeholders})", converted)
            database.execute(f"COPY snapshot_data TO {_sql_string(output)} (FORMAT PARQUET)")
        finally:
            database.close()
