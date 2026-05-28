"""Isolated read-only Python execution for chat analysis runs."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

class ReadOnlyExecutionBlockedError(ValueError):
    """Raised when generated code attempts a write-like operation."""


_WRITE_SQL_KEYWORDS = {
    "ALTER",
    "ATTACH",
    "COPY",
    "CREATE",
    "DELETE",
    "DROP",
    "EXPORT",
    "IMPORT",
    "INSERT",
    "INSTALL",
    "LOAD",
    "PRAGMA",
    "REPLACE",
    "TRUNCATE",
    "UPDATE",
    "VACUUM",
}

_BLOCKED_CALLS = {
    "open",
    "exec",
    "eval",
    "compile",
}

_BLOCKED_ATTR_CALLS = {
    ("duckdb", "connect"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("shutil", "rmtree"),
    ("shutil", "move"),
    ("shutil", "copy"),
    ("shutil", "copyfile"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("pathlib", "Path"),
}


def _normalize_filesystem_path(path: str) -> str:
    """Normalize a local path for same-file checks across Windows and POSIX."""
    value = str(path or "").strip()
    if not value:
        return ""
    return os.path.normcase(os.path.abspath(os.path.expanduser(value)))


def _strip_sql_comments(sql: str) -> str:
    lines: list[str] = []
    for line in str(sql or "").splitlines():
        before_comment = line.split("--", 1)[0]
        if before_comment.strip():
            lines.append(before_comment)
    return "\n".join(lines)


def _first_sql_keyword(sql: str) -> str:
    cleaned = _strip_sql_comments(sql).lstrip(" \t\r\n(")
    token = []
    for char in cleaned:
        if char.isalpha() or char == "_":
            token.append(char)
            continue
        break
    return "".join(token).upper()


def assert_readonly_sql(sql: str) -> None:
    """Reject SQL that starts with a write/admin keyword."""
    keyword = _first_sql_keyword(sql)
    if keyword in _WRITE_SQL_KEYWORDS:
        raise ReadOnlyExecutionBlockedError(
            f"Blocked write-like SQL statement: {keyword}. Analysis runs are read-only."
        )


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


def _call_name(node: ast.AST) -> tuple[str | None, str | None]:
    if isinstance(node, ast.Name):
        return None, node.id
    if isinstance(node, ast.Attribute):
        base = node.value
        if isinstance(base, ast.Name):
            return base.id, node.attr
        if isinstance(base, ast.Attribute):
            _, parent_attr = _call_name(base)
            return parent_attr, node.attr
    return None, None


def assert_readonly_python(code: str) -> None:
    """Reject obvious filesystem, subprocess, DuckDB write, and write-SQL attempts."""
    try:
        tree = ast.parse(str(code or ""))
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".", 1)[0] for alias in getattr(node, "names", [])]
            module = getattr(node, "module", None)
            if module:
                names.append(str(module).split(".", 1)[0])
            if any(name in {"subprocess"} for name in names):
                raise ReadOnlyExecutionBlockedError(
                    "Blocked subprocess import. Analysis runs are read-only."
                )

        if not isinstance(node, ast.Call):
            continue

        owner, name = _call_name(node.func)
        if owner is None and name in _BLOCKED_CALLS:
            if name == "open":
                mode = "r"
                if len(node.args) >= 2:
                    mode = _literal_string(node.args[1]) or mode
                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode = _literal_string(keyword.value) or mode
                if any(flag in mode for flag in ("w", "a", "x", "+")):
                    raise ReadOnlyExecutionBlockedError(
                        "Blocked writable file open. Analysis runs are read-only."
                    )
            else:
                raise ReadOnlyExecutionBlockedError(
                    f"Blocked unsafe Python call: {name}. Analysis runs are read-only."
                )

        if owner and name and (owner, name) in _BLOCKED_ATTR_CALLS:
            if (owner, name) == ("duckdb", "connect"):
                read_only = None
                for keyword in node.keywords:
                    if keyword.arg == "read_only" and isinstance(keyword.value, ast.Constant):
                        read_only = bool(keyword.value.value)
                if read_only is not True:
                    raise ReadOnlyExecutionBlockedError(
                        "Blocked writable DuckDB connection. Use the provided read-only conn."
                    )
            else:
                raise ReadOnlyExecutionBlockedError(
                    f"Blocked unsafe Python call: {owner}.{name}. Analysis runs are read-only."
                )

        if name in {"execute", "sql"} and node.args:
            sql_literal = _literal_string(node.args[0])
            if sql_literal:
                assert_readonly_sql(sql_literal)


@dataclass(frozen=True)
class ReadOnlyPythonExecutionService:
    """Execute generated Python in a separate read-only worker process."""

    max_parallel_per_workspace: int = 4
    _workspace_semaphores: dict[str, asyncio.Semaphore] = field(init=False, repr=False)
    _semaphores_lock: asyncio.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_workspace_semaphores", {})
        object.__setattr__(self, "_semaphores_lock", asyncio.Lock())

    async def execute(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        code: str,
        timeout: int,
        run_id: str,
    ) -> dict[str, Any]:
        assert_readonly_python(code)
        semaphore = await self._semaphore_for_workspace(workspace_id)
        async with semaphore:
            return await self._execute_process(
                workspace_id=workspace_id,
                workspace_duckdb_path=workspace_duckdb_path,
                code=code,
                timeout=timeout,
                run_id=run_id,
            )

    async def _semaphore_for_workspace(self, workspace_id: str) -> asyncio.Semaphore:
        async with self._semaphores_lock:
            semaphores: dict[str, asyncio.Semaphore] = getattr(self, "_workspace_semaphores")
            key = str(workspace_id or "")
            semaphore = semaphores.get(key)
            if semaphore is None:
                semaphore = asyncio.Semaphore(max(1, int(self.max_parallel_per_workspace)))
                semaphores[key] = semaphore
            return semaphore

    async def _execute_process(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        code: str,
        timeout: int,
        run_id: str,
    ) -> dict[str, Any]:
        db_path = Path(workspace_duckdb_path).expanduser().resolve(strict=False)
        worker_code = _build_worker_code(
            workspace_id=workspace_id,
            workspace_duckdb_path=str(db_path),
            workspace_duckdb_path_key=_normalize_filesystem_path(str(db_path)),
            run_id=run_id,
            user_code=code,
        )
        started = time.perf_counter()
        with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as handle:
            handle.write(worker_code)
            script_path = handle.name
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                script_path,
                cwd=str(db_path.parent),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=max(1, int(timeout)),
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return _error_payload(
                    f"Read-only execution timed out after {timeout} seconds.",
                    duration_ms=started,
                )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            payload = _extract_worker_payload(stdout)
            if payload is None:
                return {
                    **_error_payload(
                        stderr.strip() or "Read-only worker did not return a result payload.",
                        duration_ms=started,
                    ),
                    "stdout": stdout,
                    "stderr": stderr,
                }
            stripped_stdout = _strip_worker_payload(stdout)
            if not str(payload.get("stdout") or "").strip() and stripped_stdout:
                payload["stdout"] = stripped_stdout
            if not str(payload.get("stderr") or "").strip() and stderr:
                payload["stderr"] = stderr
            payload.setdefault("duration_ms", max(1, int((time.perf_counter() - started) * 1000)))
            return payload
        finally:
            try:
                Path(script_path).unlink(missing_ok=True)
            except Exception:
                pass


def _extract_worker_payload(stdout: str) -> dict[str, Any] | None:
    prefix = "__INQUIRA_READONLY_RESULT__"
    for line in reversed(str(stdout or "").splitlines()):
        if line.startswith(prefix):
            try:
                payload = json.loads(line[len(prefix):])
            except json.JSONDecodeError:
                return None
            return payload if isinstance(payload, dict) else None
    return None


def _strip_worker_payload(stdout: str) -> str:
    prefix = "__INQUIRA_READONLY_RESULT__"
    return "\n".join(
        line for line in str(stdout or "").splitlines() if not line.startswith(prefix)
    )


def _error_payload(message: str, *, duration_ms: float) -> dict[str, Any]:
    return {
        "success": False,
        "stdout": "",
        "stderr": str(message or ""),
        "has_stdout": False,
        "has_stderr": bool(message),
        "error": str(message or ""),
        "result": None,
        "result_type": None,
        "result_kind": "error",
        "result_name": None,
        "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
        "artifacts": [],
        "duration_ms": max(1, int((time.perf_counter() - duration_ms) * 1000)),
    }


def _build_worker_code(
    *,
    workspace_id: str,
    workspace_duckdb_path: str,
    workspace_duckdb_path_key: str,
    run_id: str,
    user_code: str,
) -> str:
    return textwrap.dedent(
        f"""
        import json as _json
        import sys as _sys
        import traceback as _traceback
        import uuid as _uuid
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        from pathlib import Path as _Path

        import duckdb as _duckdb

        _WORKSPACE_ID = {workspace_id!r}
        _WORKSPACE_DB_PATH = {workspace_duckdb_path!r}
        _WORKSPACE_DB_PATH_KEY = {workspace_duckdb_path_key!r}
        _RUN_ID = {run_id!r}
        _RESULT_PREFIX = "__INQUIRA_READONLY_RESULT__"
        _WRITE_SQL_KEYWORDS = {_WRITE_SQL_KEYWORDS!r}
        _inquira_run_exports = {{}}
        _inquira_active_run_id = None
        _inquira_active_turn_context = {{}}
        _inquira_workspace_id = _WORKSPACE_ID
        _inquira_ttl_hours = 48

        def _first_sql_keyword(sql):
            cleaned_lines = []
            for line in str(sql or "").splitlines():
                before = line.split("--", 1)[0]
                if before.strip():
                    cleaned_lines.append(before)
            cleaned = "\\n".join(cleaned_lines).lstrip(" \\t\\r\\n(")
            token = []
            for char in cleaned:
                if char.isalpha() or char == "_":
                    token.append(char)
                    continue
                break
            return "".join(token).upper()

        def _assert_readonly_sql(sql):
            keyword = _first_sql_keyword(sql)
            if keyword in _WRITE_SQL_KEYWORDS:
                raise PermissionError(f"Blocked write-like SQL statement: {{keyword}}. Analysis runs are read-only.")

        def _normalize_filesystem_path(path):
            import os as _os
            value = str(path or "").strip()
            if not value:
                return ""
            return _os.path.normcase(_os.path.abspath(_os.path.expanduser(value)))

        def _is_workspace_db_path(path):
            return _normalize_filesystem_path(path) == _WORKSPACE_DB_PATH_KEY

        class _ReadOnlyDuckDBConnection:
            def __init__(self, inner):
                self._inner = inner
            def execute(self, sql, *args, **kwargs):
                _assert_readonly_sql(sql)
                return self._inner.execute(sql, *args, **kwargs)
            def sql(self, sql, *args, **kwargs):
                _assert_readonly_sql(sql)
                return self._inner.sql(sql, *args, **kwargs)
            def __getattr__(self, name):
                return getattr(self._inner, name)

        _original_duckdb_connect = _duckdb.connect
        def _guarded_duckdb_connect(database=None, *args, **kwargs):
            candidate = str(database or "")
            if _is_workspace_db_path(candidate):
                if kwargs.get("read_only") is not True:
                    raise PermissionError("Blocked writable DuckDB connection to workspace DB. Analysis runs are read-only.")
                return _ReadOnlyDuckDBConnection(_original_duckdb_connect(database, *args, **kwargs))
            return _original_duckdb_connect(database, *args, **kwargs)
        _duckdb.connect = _guarded_duckdb_connect
        duckdb = _duckdb

        conn = _ReadOnlyDuckDBConnection(_original_duckdb_connect(_WORKSPACE_DB_PATH, read_only=True))
        def _inquira_now_and_expiry():
            now = _dt.now(_tz.utc)
            return now, now + _td(hours=max(1, int(_inquira_ttl_hours)))

        def _inquira_safe_name(name):
            cleaned = "".join(ch if (str(ch).isalnum() or str(ch) in "._-") else "_" for ch in str(name or "artifact"))
            cleaned = "_".join(part for part in cleaned.split("_") if part)
            return (cleaned[:96].strip("._-") or "artifact")

        def set_active_run(run_id, conversation_id=None, turn_id=None, artifact_dir=None):
            global _inquira_active_run_id, _inquira_active_turn_context
            _inquira_active_run_id = str(run_id)
            _inquira_run_exports.setdefault(_inquira_active_run_id, [])
            if conversation_id is not None or turn_id is not None or artifact_dir is not None:
                _inquira_active_turn_context[_inquira_active_run_id] = {{
                    "conversation_id": str(conversation_id or ""),
                    "turn_id": str(turn_id or ""),
                    "artifact_dir": str(artifact_dir or ""),
                }}
            return _inquira_active_run_id

        def _inquira_get_active_exports(run_id=None):
            key = str(run_id or _inquira_active_run_id or "")
            return list(_inquira_run_exports.get(key, []))

        def _inquira_artifact_path(run_id, artifact_id, kind):
            context = _inquira_active_turn_context.get(str(run_id), {{}})
            artifact_dir = str(context.get("artifact_dir") or "")
            if not artifact_dir:
                raise ValueError("No artifact_dir set. Call set_active_run(run_id, artifact_dir=...) first.")
            extension = {{"dataframe": "parquet", "figure": "json", "scalar": "json", "structured": "json", "text": "txt"}}.get(str(kind), "json")
            target = _Path(artifact_dir).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            return target / (str(artifact_id) + "." + extension)

        def _inquira_named_artifact_id(logical_name, kind):
            return _inquira_safe_name(logical_name or kind or "artifact") + "__" + str(_uuid.uuid4())

        def _inquira_replace_run_export(run_id, kind, logical_name, envelope):
            existing = []
            for item in _inquira_run_exports.get(str(run_id), []):
                if str(item.get("kind")) == str(kind) and str(item.get("logical_name")) == str(logical_name):
                    old_path = str(item.get("storage_path") or "")
                    if old_path:
                        try:
                            _Path(old_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                    continue
                existing.append(item)
            existing.append(envelope)
            _inquira_run_exports[str(run_id)] = existing

        def _inquira_export_envelope(*, artifact_id, run_id, kind, logical_name, storage_path=None, table_name=None, row_count=None, schema=None, preview_rows=None, payload=None, status='ready', error=None):
            now, expires = _inquira_now_and_expiry()
            context = _inquira_active_turn_context.get(str(run_id), {{}})
            return {{
                "artifact_id": str(artifact_id),
                "run_id": str(run_id),
                "kind": str(kind),
                "pointer": str(storage_path or ""),
                "storage_path": str(storage_path or ""),
                "conversation_id": str(context.get("conversation_id") or ""),
                "turn_id": str(context.get("turn_id") or ""),
                "logical_name": str(logical_name),
                "row_count": int(row_count) if row_count is not None else None,
                "schema": schema,
                "preview_rows": preview_rows or [],
                "payload": payload,
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
                "status": status,
                "error": error,
                "table_name": table_name,
            }}

        def export_dataframe(df, logical_name, run_id=None, title=None, insight=None):
            active_run = str(run_id or _inquira_active_run_id or "")
            if not active_run:
                raise ValueError("No active run_id set. Call set_active_run(run_id) first.")
            import pandas as _pd
            try:
                import polars as _pl
            except Exception:
                _pl = None
            try:
                import pyarrow as _pa
            except Exception:
                _pa = None
            if _pl is not None and isinstance(df, _pl.LazyFrame):
                df = df.collect()
            if _pl is not None and isinstance(df, _pl.DataFrame):
                pdf = df.to_pandas()
            elif _pa is not None and isinstance(df, _pa.Table):
                pdf = df.to_pandas()
            elif _pa is not None and isinstance(df, _pa.RecordBatch):
                pdf = _pa.Table.from_batches([df]).to_pandas()
            elif _pa is not None and hasattr(_pa, "RecordBatchReader") and isinstance(df, _pa.RecordBatchReader):
                pdf = df.read_all().to_pandas()
            elif isinstance(df, _pd.DataFrame):
                pdf = df
            else:
                pdf = _pd.DataFrame(df)
            artifact_id = _inquira_named_artifact_id(logical_name, "dataframe")
            storage_path = _inquira_artifact_path(active_run, artifact_id, "dataframe")
            _export_con = _original_duckdb_connect(":memory:")
            try:
                _export_con.register("_inquira_df_tmp", pdf)
                _safe_storage_path = str(storage_path).replace("'", "''")
                _export_con.execute(f"COPY (SELECT * FROM _inquira_df_tmp) TO '{{_safe_storage_path}}' (FORMAT PARQUET)")
            finally:
                try:
                    _export_con.unregister("_inquira_df_tmp")
                except Exception:
                    pass
                _export_con.close()
            row_count = int(len(pdf.index))
            schema = [{{"name": str(col), "dtype": str(dtype)}} for col, dtype in pdf.dtypes.items()]
            preview_rows = _json.loads(pdf.head(20).to_json(orient="records", date_format="iso"))
            envelope = _inquira_export_envelope(
                artifact_id=artifact_id,
                run_id=active_run,
                kind="dataframe",
                logical_name=str(logical_name),
                storage_path=str(storage_path),
                row_count=row_count,
                schema=schema,
                preview_rows=preview_rows,
                payload={{"title": title, "insight": insight}},
            )
            _inquira_replace_run_export(active_run, "dataframe", str(logical_name), envelope)
            return envelope

        def export_figure(fig, logical_name, run_id=None, title=None, insight=None):
            active_run = str(run_id or _inquira_active_run_id or "")
            if not active_run:
                raise ValueError("No active run_id set. Call set_active_run(run_id) first.")
            try:
                import plotly.graph_objects as _go
            except Exception:
                _go = None
            if _go is not None and isinstance(fig, _go.Figure):
                fig_payload = _json.loads(fig.to_json())
            else:
                fig_payload = _json.loads(_json.dumps(fig, default=str))
            artifact_id = _inquira_named_artifact_id(logical_name, "figure")
            storage_path = _inquira_artifact_path(active_run, artifact_id, "figure")
            payload = {{"figure": fig_payload, "title": title, "insight": insight}}
            storage_path.write_text(_json.dumps(payload, default=str), encoding="utf-8")
            envelope = _inquira_export_envelope(
                artifact_id=artifact_id,
                run_id=active_run,
                kind="figure",
                logical_name=str(logical_name),
                storage_path=str(storage_path),
                payload=payload,
            )
            _inquira_replace_run_export(active_run, "figure", str(logical_name), envelope)
            return envelope

        def export_scalar(value, logical_name, run_id=None, meta=None):
            active_run = str(run_id or _inquira_active_run_id or "")
            if not active_run:
                raise ValueError("No active run_id set. Call set_active_run(run_id) first.")
            artifact_id = _inquira_named_artifact_id(logical_name, "scalar")
            storage_path = _inquira_artifact_path(active_run, artifact_id, "scalar")
            payload = {{"value": value, "meta": meta}}
            storage_path.write_text(_json.dumps(payload, default=str), encoding="utf-8")
            envelope = _inquira_export_envelope(
                artifact_id=artifact_id,
                run_id=active_run,
                kind="scalar",
                logical_name=str(logical_name),
                storage_path=str(storage_path),
                payload=payload,
            )
            _inquira_replace_run_export(active_run, "scalar", str(logical_name), envelope)
            return envelope

        def finalize_run(run_id, metadata=None):
            active_run = str(run_id or _inquira_active_run_id or "")
            if not active_run:
                raise ValueError("No run_id provided to finalize_run")
            return {{"run_id": active_run, "exports": list(_inquira_run_exports.get(active_run, []))}}

        def _json_safe(value):
            try:
                _json.dumps(value, default=str, allow_nan=False)
                return value
            except Exception:
                return str(value)

        try:
            set_active_run(_RUN_ID)
            exec({user_code!r}, globals(), globals())
            finalize_run(_RUN_ID, metadata={{"execution_status": "success"}})
            _payload = {{
                "success": True,
                "stdout": "",
                "stderr": "",
                "has_stdout": False,
                "has_stderr": False,
                "error": None,
                "result": None,
                "result_type": None,
                "result_kind": "none",
                "result_name": None,
                "variables": {{"dataframes": {{}}, "figures": {{}}, "scalars": {{}}}},
                "artifacts": _inquira_get_active_exports(_RUN_ID),
            }}
        except BaseException as _exc:
            _payload = {{
                "success": False,
                "stdout": "",
                "stderr": str(_exc),
                "has_stdout": False,
                "has_stderr": True,
                "error": str(_exc),
                "result": None,
                "result_type": None,
                "result_kind": "error",
                "result_name": None,
                "variables": {{"dataframes": {{}}, "figures": {{}}, "scalars": {{}}}},
                "artifacts": _inquira_get_active_exports(_RUN_ID),
            }}
            _traceback.print_exc(file=_sys.stderr)
        print(_RESULT_PREFIX + _json.dumps(_json_safe(_payload), default=str, allow_nan=False))
        """
    )
