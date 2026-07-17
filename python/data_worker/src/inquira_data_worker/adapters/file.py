"""DuckDB-backed single-file adapters."""

from __future__ import annotations

import datetime as dt
import decimal
import hashlib
from pathlib import Path
from typing import Any

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

MAX_PREVIEW_ROWS = 1000


def _sql_string(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _json_value(value: Any) -> Any:
    if isinstance(value, (dt.date, dt.datetime, dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


class FileAdapter:
    kind: str
    suffix: str
    reader: str

    def _source(self, value: str) -> Path:
        if not str(value or "").strip():
            raise AdapterError("invalid_params", "A source path is required.")
        raw = Path(value).expanduser()
        if not raw.exists():
            raise AdapterError("source_not_found", f"Source file does not exist: {raw}")
        if not raw.is_file():
            raise AdapterError("source_not_file", "Source path must be a regular file.")
        if raw.suffix.lower() != self.suffix:
            raise AdapterError("source_extension_mismatch", f"Expected a {self.suffix} file extension.")
        if raw.stat().st_size == 0:
            raise AdapterError("source_unreadable", f"Could not read {self.kind} source: file is empty.")
        return raw.resolve(strict=True)

    def _relation(self, path: Path) -> str:
        return f"{self.reader}({_sql_string(path)})"

    def _columns(self, connection: duckdb.DuckDBPyConnection, path: Path) -> list[Column]:
        try:
            rows = connection.execute(f"DESCRIBE SELECT * FROM {self._relation(path)}").fetchall()
        except Exception as exc:
            raise AdapterError("source_unreadable", f"Could not read {self.kind} source: {exc}") from exc
        if not rows:
            raise AdapterError("source_unreadable", f"Could not read {self.kind} source: no columns found.")
        return [Column(name=str(row[0]), data_type=str(row[1]), nullable=str(row[2]).upper() != "NO") for row in rows]

    def discover(self, request: AdapterRequest) -> Discovery:
        path = self._source(request.source_path)
        connection = duckdb.connect()
        try:
            columns = self._columns(connection, path)
        finally:
            connection.close()
        return Discovery(
            adapter_kind=self.kind,
            source_path=str(path),
            fingerprint=_fingerprint(path),
            objects=[SourceObject(id="file", name=path.stem, kind="table", columns=columns)],
        )

    def preview(self, request: AdapterRequest, limit: int) -> Preview:
        if limit < 1 or limit > MAX_PREVIEW_ROWS:
            raise AdapterError("invalid_preview_limit", f"Preview limit must be between 1 and {MAX_PREVIEW_ROWS}.")
        path = self._source(request.source_path)
        connection = duckdb.connect()
        try:
            columns = self._columns(connection, path)
            rows = connection.execute(f"SELECT * FROM {self._relation(path)} LIMIT ?", [limit + 1]).fetchall()
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError("source_unreadable", f"Could not read {self.kind} source: {exc}") from exc
        finally:
            connection.close()
        names = [column.name for column in columns]
        return Preview(
            columns=columns,
            rows=[{name: _json_value(value) for name, value in zip(names, row, strict=True)} for row in rows[:limit]],
            truncated=len(rows) > limit,
        )

    def materialize(self, request: MaterializeRequest) -> Materialization:
        if request.selected_object_ids != ["file"]:
            raise AdapterError("invalid_selection", "Single-file adapters require the file object selection.")
        path = self._source(request.source_path)
        target = Path(request.target_dir).expanduser().resolve()
        if target.exists() and any(target.iterdir()):
            raise AdapterError("target_not_empty", "Materialization target must be empty.")
        target.mkdir(parents=True, exist_ok=True)
        output = target / "data.parquet"
        before = _fingerprint(path)
        connection = duckdb.connect()
        try:
            columns = self._columns(connection, path)
            connection.execute(
                f"COPY (SELECT * FROM {self._relation(path)}) TO {_sql_string(output)} (FORMAT PARQUET)"
            )
            row_count = int(connection.execute(f"SELECT count(*) FROM read_parquet({_sql_string(output)})").fetchone()[0])
        except AdapterError:
            raise
        except Exception as exc:
            output.unlink(missing_ok=True)
            raise AdapterError("materialization_failed", f"Could not materialize {self.kind} source: {exc}") from exc
        finally:
            connection.close()
        after = _fingerprint(path)
        if after != before:
            output.unlink(missing_ok=True)
            raise AdapterError("source_changed", "Source file changed during materialization; refresh again.")
        return Materialization(
            fingerprint=after,
            outputs=[MaterializedOutput(
                source_object_id="file",
                name=path.stem,
                relative_path="data.parquet",
                format="parquet",
                columns=columns,
                row_count=row_count,
                byte_size=output.stat().st_size,
            )],
        )


class CSVAdapter(FileAdapter):
    kind = "csv"
    suffix = ".csv"
    reader = "read_csv"


class ParquetAdapter(FileAdapter):
    kind = "parquet"
    suffix = ".parquet"
    reader = "read_parquet"
