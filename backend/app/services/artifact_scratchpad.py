"""Workspace scratchpad artifact persistence and retrieval utilities."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb


_DEFAULT_TTL_HOURS = 48


@dataclass(frozen=True)
class ScratchpadConfig:
    ttl_hours: int = _DEFAULT_TTL_HOURS
    max_bytes: int = 10 * 1024 * 1024 * 1024


class ArtifactScratchpadStore:
    """Manifest-backed artifact store per workspace scratchpad."""

    def __init__(self, config: ScratchpadConfig | None = None) -> None:
        self._config = config or ScratchpadConfig()

    @staticmethod
    def build_scratchpad_dir(workspace_duckdb_path: str) -> Path:
        return Path(workspace_duckdb_path).parent / "scratchpad"

    @staticmethod
    def build_scratchpad_db_path(workspace_duckdb_path: str) -> Path:
        return ArtifactScratchpadStore.build_scratchpad_dir(workspace_duckdb_path) / "artifacts.duckdb"

    @staticmethod
    def _quoted(ident: str) -> str:
        return '"' + str(ident).replace('"', '""') + '"'

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _build_single_filter_clause(
        cls,
        *,
        model: dict[str, Any],
        quoted_column: str,
    ) -> tuple[str, list[Any]]:
        if not isinstance(model, dict):
            return "", []

        operator = str(model.get("operator") or "").upper()
        nested_conditions: list[dict[str, Any]] = []
        if isinstance(model.get("conditions"), list):
            nested_conditions = [item for item in model["conditions"] if isinstance(item, dict)]
        else:
            condition_one = model.get("condition1")
            condition_two = model.get("condition2")
            if isinstance(condition_one, dict):
                nested_conditions.append(condition_one)
            if isinstance(condition_two, dict):
                nested_conditions.append(condition_two)

        if nested_conditions:
            nested_sql_parts: list[str] = []
            nested_params: list[Any] = []
            joiner = " OR " if operator == "OR" else " AND "
            for nested_model in nested_conditions:
                clause, clause_params = cls._build_single_filter_clause(
                    model=nested_model,
                    quoted_column=quoted_column,
                )
                if not clause:
                    continue
                nested_sql_parts.append(f"({clause})")
                nested_params.extend(clause_params)
            if not nested_sql_parts:
                return "", []
            return joiner.join(nested_sql_parts), nested_params

        filter_type = str(model.get("filterType") or "").lower()
        filter_mode = str(model.get("type") or "").strip()

        if filter_type == "set":
            raw_values = model.get("values")
            if not isinstance(raw_values, list):
                return "", []
            if not raw_values:
                return "1 = 0", []
            placeholders = ", ".join(["?"] * len(raw_values))
            return f"{quoted_column} IN ({placeholders})", list(raw_values)

        if filter_mode == "blank":
            return f"({quoted_column} IS NULL OR CAST({quoted_column} AS VARCHAR) = '')", []
        if filter_mode == "notBlank":
            return f"({quoted_column} IS NOT NULL AND CAST({quoted_column} AS VARCHAR) <> '')", []

        if filter_type == "text":
            haystack = f"LOWER(CAST({quoted_column} AS VARCHAR))"
            value = str(model.get("filter") or "").lower()
            if filter_mode == "contains":
                return f"{haystack} LIKE ?", [f"%{value}%"]
            if filter_mode == "notContains":
                return f"({quoted_column} IS NULL OR {haystack} NOT LIKE ?)", [f"%{value}%"]
            if filter_mode == "equals":
                return f"{haystack} = ?", [value]
            if filter_mode == "notEqual":
                return f"({quoted_column} IS NULL OR {haystack} <> ?)", [value]
            if filter_mode == "startsWith":
                return f"{haystack} LIKE ?", [f"{value}%"]
            if filter_mode == "endsWith":
                return f"{haystack} LIKE ?", [f"%{value}"]
            return "", []

        if filter_type == "number":
            numeric_expr = f"TRY_CAST({quoted_column} AS DOUBLE)"
            number_value = cls._coerce_float(model.get("filter"))
            number_to_value = cls._coerce_float(model.get("filterTo"))
            if filter_mode == "equals" and number_value is not None:
                return f"{numeric_expr} = ?", [number_value]
            if filter_mode == "notEqual" and number_value is not None:
                return f"({numeric_expr} IS NULL OR {numeric_expr} <> ?)", [number_value]
            if filter_mode == "greaterThan" and number_value is not None:
                return f"{numeric_expr} > ?", [number_value]
            if filter_mode == "greaterThanOrEqual" and number_value is not None:
                return f"{numeric_expr} >= ?", [number_value]
            if filter_mode == "lessThan" and number_value is not None:
                return f"{numeric_expr} < ?", [number_value]
            if filter_mode == "lessThanOrEqual" and number_value is not None:
                return f"{numeric_expr} <= ?", [number_value]
            if filter_mode == "inRange" and number_value is not None and number_to_value is not None:
                low, high = sorted([number_value, number_to_value])
                return f"{numeric_expr} BETWEEN ? AND ?", [low, high]
            return "", []

        if filter_type == "date":
            date_expr = f"TRY_CAST({quoted_column} AS TIMESTAMP)"
            date_value = model.get("dateFrom") or model.get("filter")
            date_to_value = model.get("dateTo") or model.get("filterTo")
            if filter_mode == "equals" and date_value:
                return f"{date_expr} = TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
            if filter_mode == "notEqual" and date_value:
                return (
                    f"({date_expr} IS NULL OR {date_expr} <> TRY_CAST(? AS TIMESTAMP))",
                    [str(date_value)],
                )
            if filter_mode == "greaterThan" and date_value:
                return f"{date_expr} > TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
            if filter_mode == "greaterThanOrEqual" and date_value:
                return f"{date_expr} >= TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
            if filter_mode == "lessThan" and date_value:
                return f"{date_expr} < TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
            if filter_mode == "lessThanOrEqual" and date_value:
                return f"{date_expr} <= TRY_CAST(? AS TIMESTAMP)", [str(date_value)]
            if filter_mode == "inRange" and date_value and date_to_value:
                return (
                    f"{date_expr} BETWEEN TRY_CAST(? AS TIMESTAMP) AND TRY_CAST(? AS TIMESTAMP)",
                    [str(date_value), str(date_to_value)],
                )
            return "", []

        if filter_type == "boolean":
            value = model.get("filter")
            if isinstance(value, bool):
                return (f"TRY_CAST({quoted_column} AS BOOLEAN) IS {'TRUE' if value else 'FALSE'}", [])
            value_text = str(value).strip().lower()
            if value_text in {"true", "false"}:
                return (f"TRY_CAST({quoted_column} AS BOOLEAN) IS {value_text.upper()}", [])
            return "", []

        return "", []

    @classmethod
    def build_dataframe_where_clause(
        cls,
        *,
        column_names: list[str],
        filter_model: dict[str, Any] | None = None,
        search_text: str | None = None,
    ) -> tuple[str, list[Any]]:
        quoted_columns = {str(name): cls._quoted(str(name)) for name in column_names}
        where_parts: list[str] = []
        where_params: list[Any] = []

        safe_filter_model = filter_model if isinstance(filter_model, dict) else {}
        for raw_col_id, raw_model in safe_filter_model.items():
            quoted_column = quoted_columns.get(str(raw_col_id))
            if not quoted_column or not isinstance(raw_model, dict):
                continue
            clause, params = cls._build_single_filter_clause(
                model=raw_model,
                quoted_column=quoted_column,
            )
            if not clause:
                continue
            where_parts.append(f"({clause})")
            where_params.extend(params)

        needle = str(search_text or "").strip().lower()
        if needle and quoted_columns:
            search_clauses = [f"LOWER(CAST({expr} AS VARCHAR)) LIKE ?" for expr in quoted_columns.values()]
            where_parts.append(f"({' OR '.join(search_clauses)})")
            where_params.extend([f"%{needle}%"] * len(search_clauses))

        if not where_parts:
            return "", []
        return f"WHERE {' AND '.join(where_parts)}", where_params

    @classmethod
    def build_dataframe_order_clause(
        cls,
        *,
        column_names: list[str],
        sort_model: list[dict[str, Any]] | None = None,
    ) -> str:
        quoted_columns = {str(name): cls._quoted(str(name)) for name in column_names}
        safe_sort_model = sort_model if isinstance(sort_model, list) else []
        order_parts: list[str] = []

        for entry in safe_sort_model:
            if not isinstance(entry, dict):
                continue
            quoted_column = quoted_columns.get(str(entry.get("colId") or ""))
            direction = str(entry.get("sort") or "").lower()
            if not quoted_column or direction not in {"asc", "desc"}:
                continue
            order_parts.append(f"{quoted_column} {direction.upper()}")

        if not order_parts:
            return ""
        return f"ORDER BY {', '.join(order_parts)}"

    @staticmethod
    def _safe_table_name(run_id: str, seq: int) -> str:
        run_short = re.sub(r"[^A-Za-z0-9]", "", str(run_id))[:12] or "run"
        return f"art_{run_short}_{max(1, int(seq))}"

    @staticmethod
    def _is_lock_conflict(exc: duckdb.IOException) -> bool:
        return "Conflicting lock is held" in str(exc)

    @staticmethod
    def _open_readonly(workspace_duckdb_path: str) -> duckdb.DuckDBPyConnection | None:
        """Open the scratchpad DB read-only; return *None* if the file doesn't exist.

        If a conflicting write lock is held (e.g. by the workspace kernel), this
        will raise ``duckdb.IOException`` — the caller / API layer should catch
        it and fall back to the kernel's in-process scratchpad connection.
        """
        db_path = ArtifactScratchpadStore.build_scratchpad_db_path(workspace_duckdb_path)
        if not db_path.exists():
            return None
        return duckdb.connect(str(db_path), read_only=True)

    def ensure_workspace(self, workspace_duckdb_path: str) -> Path:
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS artifact_manifest (
                    artifact_id VARCHAR PRIMARY KEY,
                    run_id VARCHAR NOT NULL,
                    workspace_id VARCHAR NOT NULL,
                    logical_name VARCHAR NOT NULL,
                    kind VARCHAR NOT NULL,
                    table_name VARCHAR,
                    payload_json TEXT,
                    schema_json TEXT,
                    row_count BIGINT,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    status VARCHAR NOT NULL,
                    error TEXT
                )
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_manifest_run_id
                ON artifact_manifest(run_id)
                """
            )
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_manifest_workspace_id
                ON artifact_manifest(workspace_id)
                """
            )
            # Enforce: at most one live artifact per (workspace_id, kind, logical_name).
            # Using CREATE UNIQUE INDEX (not inline UNIQUE) so this is applied even when
            # the table already existed without the constraint (stale DBs from older versions).
            con.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_artifact_manifest_unique_name
                ON artifact_manifest(workspace_id, kind, logical_name)
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS run_manifest (
                    run_id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    conversation_id VARCHAR,
                    turn_id VARCHAR,
                    question TEXT,
                    generated_code TEXT,
                    executed_code TEXT,
                    stdout TEXT,
                    stderr TEXT,
                    execution_status VARCHAR NOT NULL,
                    retry_count INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
                """
            )
        finally:
            con.close()
        return db_path

    def write_run_manifest(
        self,
        *,
        workspace_duckdb_path: str,
        run_id: str,
        workspace_id: str,
        conversation_id: str | None,
        turn_id: str | None,
        question: str,
        generated_code: str,
        executed_code: str,
        stdout: str,
        stderr: str,
        execution_status: str,
        retry_count: int,
    ) -> None:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=max(1, self._config.ttl_hours))
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                INSERT OR REPLACE INTO run_manifest (
                    run_id, workspace_id, conversation_id, turn_id, question,
                    generated_code, executed_code, stdout, stderr,
                    execution_status, retry_count, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id,
                    workspace_id,
                    conversation_id,
                    turn_id,
                    question,
                    generated_code,
                    executed_code,
                    stdout,
                    stderr,
                    execution_status,
                    int(retry_count),
                    now,
                    expires_at,
                ],
            )
        finally:
            con.close()

    def store_script_artifact(
        self,
        *,
        workspace_duckdb_path: str,
        workspace_id: str,
        run_id: str,
        script_text: str,
        logical_name: str = "final_script",
    ) -> str:
        db_path = self.ensure_workspace(workspace_duckdb_path)
        artifact_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=max(1, self._config.ttl_hours))
        payload = json.dumps({"script": script_text}, ensure_ascii=True)
        con = duckdb.connect(str(db_path), read_only=False)
        try:
            con.execute(
                """
                INSERT INTO artifact_manifest (
                    artifact_id, run_id, workspace_id, logical_name, kind,
                    table_name, payload_json, schema_json, row_count,
                    created_at, expires_at, status, error
                ) VALUES (?, ?, ?, ?, 'script', NULL, ?, NULL, NULL, ?, ?, 'ready', NULL)
                """,
                [artifact_id, run_id, workspace_id, logical_name, payload, now, expires_at],
            )
        finally:
            con.close()
        return artifact_id

    def get_artifact(self, *, workspace_duckdb_path: str, artifact_id: str) -> dict[str, Any] | None:
        con = self._open_readonly(workspace_duckdb_path)
        if con is None:
            return None
        try:
            row = con.execute(
                """
                SELECT artifact_id, run_id, workspace_id, logical_name, kind, table_name,
                       payload_json, schema_json, row_count, created_at, expires_at, status, error
                FROM artifact_manifest
                WHERE artifact_id = ?
                LIMIT 1
                """,
                [artifact_id],
            ).fetchone()
        finally:
            con.close()
        if row is None:
            return None
        schema = None
        payload = None
        try:
            if row[7]:
                schema = json.loads(str(row[7]))
        except Exception:
            schema = None
        try:
            if row[6]:
                payload = json.loads(str(row[6]))
        except Exception:
            payload = None
        return {
            "artifact_id": str(row[0]),
            "run_id": str(row[1]),
            "workspace_id": str(row[2]),
            "logical_name": str(row[3]),
            "kind": str(row[4]),
            "table_name": str(row[5]) if row[5] is not None else None,
            "payload": payload,
            "schema": schema,
            "row_count": int(row[8] or 0) if row[8] is not None else None,
            "created_at": str(row[9]),
            "expires_at": str(row[10]),
            "status": str(row[11]),
            "error": str(row[12]) if row[12] is not None else None,
            "pointer": f"duckdb://scratchpad/artifacts.duckdb#artifact={row[0]}",
        }

    def list_artifacts_for_run(self, *, workspace_duckdb_path: str, run_id: str) -> list[dict[str, Any]]:
        con = self._open_readonly(workspace_duckdb_path)
        if con is None:
            return []
        try:
            rows = con.execute(
                """
                SELECT artifact_id
                FROM artifact_manifest
                WHERE run_id = ?
                ORDER BY created_at ASC
                """,
                [run_id],
            ).fetchall()
        finally:
            con.close()
        artifacts: list[dict[str, Any]] = []
        for row in rows:
            item = self.get_artifact(workspace_duckdb_path=workspace_duckdb_path, artifact_id=str(row[0]))
            if item is None:
                continue
            artifacts.append(item)
        return artifacts

    def list_artifacts_for_workspace(
        self,
        *,
        workspace_duckdb_path: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return lightweight summaries for all non-expired artifacts in the workspace.

        Because the schema enforces UNIQUE (workspace_id, kind, logical_name), there
        is at most one live row per (kind, name) pair — no deduplication needed here.

        Items are ordered newest-first.  Pass ``kind`` (e.g. ``'dataframe'``)
        to restrict results to a single artifact type.
        """
        con = self._open_readonly(workspace_duckdb_path)
        if con is None:
            return []
        now = datetime.now(UTC)
        try:
            if kind:
                rows = con.execute(
                    """
                    SELECT artifact_id, logical_name, kind, row_count, schema_json, created_at, status
                    FROM artifact_manifest
                    WHERE kind = ? AND expires_at > ? AND status = 'ready'
                    ORDER BY created_at DESC
                    """,
                    [kind, now],
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT artifact_id, logical_name, kind, row_count, schema_json, created_at, status
                    FROM artifact_manifest
                    WHERE expires_at > ? AND status = 'ready'
                    ORDER BY created_at DESC
                    """,
                    [now],
                ).fetchall()
        finally:
            con.close()

        result: list[dict[str, Any]] = []
        for row in rows:
            schema = None
            try:
                if row[4]:
                    schema = json.loads(str(row[4]))
            except Exception:
                schema = None
            result.append(
                {
                    "artifact_id": str(row[0]),
                    "logical_name": str(row[1]),
                    "kind": str(row[2]),
                    "row_count": int(row[3] or 0) if row[3] is not None else None,
                    "schema": schema,
                    "created_at": str(row[5]),
                    "status": str(row[6]),
                }
            )
        return result

    def get_dataframe_rows(
        self,
        *,
        workspace_duckdb_path: str,
        artifact_id: str,
        offset: int,
        limit: int,
        sort_model: list[dict[str, Any]] | None = None,
        filter_model: dict[str, Any] | None = None,
        search_text: str | None = None,
    ) -> dict[str, Any] | None:
        meta = self.get_artifact(workspace_duckdb_path=workspace_duckdb_path, artifact_id=artifact_id)
        if meta is None or meta.get("kind") != "dataframe":
            return None
        table_name = str(meta.get("table_name") or "").strip()
        if not table_name:
            return None
        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(1000, int(limit)))
        con = self._open_readonly(workspace_duckdb_path)
        if con is None:
            return None
        try:
            escaped = table_name.replace('"', '""')
            schema_rows = con.execute(f'PRAGMA table_info("{escaped}")').fetchall()
            all_columns = [str(row[1]) for row in schema_rows]
            where_sql, where_params = self.build_dataframe_where_clause(
                column_names=all_columns,
                filter_model=filter_model,
                search_text=search_text,
            )
            order_sql = self.build_dataframe_order_clause(
                column_names=all_columns,
                sort_model=sort_model,
            )
            page_df = con.execute(
                f'SELECT * FROM "{escaped}" {where_sql} {order_sql} LIMIT {safe_limit} OFFSET {safe_offset}',
                where_params,
            ).fetchdf()
            rows = json.loads(page_df.to_json(orient="records", date_format="iso"))
            columns = [str(c) for c in list(page_df.columns)]
            row_count = con.execute(
                f'SELECT COUNT(*) FROM "{escaped}" {where_sql}',
                where_params,
            ).fetchone()
        finally:
            con.close()
        return {
            "artifact_id": artifact_id,
            "name": meta.get("logical_name") or "dataframe",
            "row_count": int((row_count or [0])[0] or 0),
            "columns": columns,
            "rows": rows,
            "offset": safe_offset,
            "limit": safe_limit,
        }

    def get_workspace_artifact_usage(
        self,
        *,
        workspace_duckdb_path: str,
    ) -> dict[str, int]:
        """Return lightweight scratchpad usage metrics for workspace warning UX."""
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        duckdb_bytes = int(db_path.stat().st_size) if db_path.exists() else 0
        con = self._open_readonly(workspace_duckdb_path)
        if con is None:
            return {"duckdb_bytes": duckdb_bytes, "figure_count": 0}

        now = datetime.now(UTC)
        try:
            row = con.execute(
                """
                SELECT COUNT(*)
                FROM artifact_manifest
                WHERE kind = 'figure' AND expires_at > ? AND status = 'ready'
                """,
                [now],
            ).fetchone()
        finally:
            con.close()

        figure_count = int((row or [0])[0] or 0)
        return {"duckdb_bytes": duckdb_bytes, "figure_count": figure_count}

    def delete_artifact(
        self,
        *,
        workspace_duckdb_path: str,
        artifact_id: str,
    ) -> bool:
        """Delete one artifact by ID.

        For dataframe artifacts, also drops the backing table (best effort).
        Returns ``True`` only when an artifact row existed and was deleted.
        """
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        if not db_path.exists():
            return False

        con = duckdb.connect(str(db_path), read_only=False)
        try:
            row = con.execute(
                """
                SELECT kind, table_name
                FROM artifact_manifest
                WHERE artifact_id = ?
                LIMIT 1
                """,
                [artifact_id],
            ).fetchone()
            if row is None:
                return False

            kind = str(row[0] or "")
            table_name = str(row[1] or "").strip()
            con.execute("DELETE FROM artifact_manifest WHERE artifact_id = ?", [artifact_id])
            if kind == "dataframe" and table_name:
                escaped = table_name.replace('"', '""')
                try:
                    con.execute(f'DROP TABLE IF EXISTS "{escaped}"')
                except Exception:
                    # Manifest delete has already succeeded; avoid surfacing stale-table cleanup errors.
                    pass
            return True
        finally:
            con.close()

    def prune_workspace(self, *, workspace_duckdb_path: str) -> None:
        db_path = self.build_scratchpad_db_path(workspace_duckdb_path)
        if not db_path.exists():
            return
        try:
            con = duckdb.connect(str(db_path), read_only=False)
        except duckdb.IOException as exc:
            # Best-effort retention cleanup: skip busy/locked workspaces and retry later.
            if self._is_lock_conflict(exc):
                return
            raise
        now = datetime.now(UTC)
        try:
            expired_tables = con.execute(
                """
                SELECT table_name
                FROM artifact_manifest
                WHERE kind = 'dataframe' AND table_name IS NOT NULL AND expires_at < ?
                """,
                [now],
            ).fetchall()
            for (table_name,) in expired_tables:
                if not table_name:
                    continue
                escaped = str(table_name).replace('"', '""')
                con.execute(f'DROP TABLE IF EXISTS "{escaped}"')
            con.execute("DELETE FROM artifact_manifest WHERE expires_at < ?", [now])
            con.execute("DELETE FROM run_manifest WHERE expires_at < ?", [now])
        finally:
            con.close()

    def prune_all(self, *, inquira_root: Path | None = None) -> None:
        root = inquira_root or (Path.home() / ".inquira")
        if not root.exists():
            return
        for artifacts_db in root.glob("*/workspaces/*/scratchpad/artifacts.duckdb"):
            workspace_duckdb_path = str(artifacts_db.parent.parent / "workspace.duckdb")
            self.prune_workspace(workspace_duckdb_path=workspace_duckdb_path)


_scratchpad_store = ArtifactScratchpadStore()


def get_artifact_scratchpad_store() -> ArtifactScratchpadStore:
    return _scratchpad_store
