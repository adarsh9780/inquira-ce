"""Workspace-scoped Jupyter kernel lifecycle and execution orchestration."""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
from jupyter_client import AsyncKernelManager

from app.services.jupyter_message_parser import (
    ParsedExecutionOutput,
    update_from_iopub_message,
)
from app.services.runner_env import ensure_runner_kernel_dependencies, resolve_runner_python

_FALLBACK_RESULT_PROBE_CODE = """
import json as _json

try:
    import pandas as _pd
except Exception:
    _pd = None

try:
    import plotly.graph_objects as _go
except Exception:
    _go = None

_inquira_target = None
for _name in ("result", "final_df", "df", "fig", "figure"):
    if _name in globals():
        _inquira_target = globals().get(_name)
        break

if _inquira_target is None:
    _inquira_target = globals().get("_")

if _inquira_target is None:
    _inquira_payload = None
elif _pd is not None and isinstance(_inquira_target, _pd.DataFrame):
    _preview = _inquira_target.head(1000)
    # Ensure the payload remains JSON-safe so Jupyter can emit application/json
    # and frontend can classify it as a dataframe instead of scalar text.
    _inquira_payload = {
        "columns": [str(c) for c in list(_preview.columns)],
        "data": _json.loads(_preview.to_json(orient="records", date_format="iso")),
    }
elif _go is not None and isinstance(_inquira_target, _go.Figure):
    _inquira_payload = _inquira_target.to_plotly_json()
else:
    _inquira_payload = _inquira_target

_inquira_payload
"""

_ARTIFACT_SYNC_CODE = """
import json as _json
import uuid as _uuid

try:
    import pandas as _pd
except Exception:
    _pd = None

try:
    import polars as _pl
except Exception:
    _pl = None

try:
    import pyarrow as _pa
except Exception:
    _pa = None

try:
    import plotly.graph_objects as _go
except Exception:
    _go = None

if "_inquira_df_artifacts" not in globals():
    _inquira_df_artifacts = {}
if "_inquira_fig_artifacts" not in globals():
    _inquira_fig_artifacts = {}

def _safe_name(name):
    cleaned = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(name))
    if not cleaned:
        cleaned = "value"
    return cleaned[:96]

def _quoted(name):
    return '"' + str(name).replace('"', '""') + '"'

def _to_pandas(value):
    if _pd is not None and isinstance(value, _pd.DataFrame):
        return value
    if _pl is not None:
        if isinstance(value, _pl.LazyFrame):
            return value.collect().to_pandas()
        if isinstance(value, _pl.DataFrame):
            return value.to_pandas()
    if _pa is not None:
        if isinstance(value, _pa.Table):
            return value.to_pandas()
        if isinstance(value, _pa.RecordBatch):
            return _pa.Table.from_batches([value]).to_pandas()
    return None

def _is_figure(value):
    if _go is not None and isinstance(value, _go.Figure):
        return True
    return isinstance(value, dict) and {"data", "layout"}.issubset(value.keys())

_bundle = {
    "dataframes": {},
    "figures": {},
    "scalars": {},
}

_seen_df_names = set()
_seen_fig_names = set()

for _name, _value in list(globals().items()):
    if _name.startswith("_"):
        continue
    _pdf = _to_pandas(_value)
    if _pdf is not None and "artifact_conn" in globals() and artifact_conn is not None:
        _seen_df_names.add(_name)
        _artifact = _inquira_df_artifacts.get(_name, {})
        _artifact_id = _artifact.get("artifact_id") or str(_uuid.uuid4())
        _table_name = f"df_{_safe_name(_name)}"
        artifact_conn.register("_inquira_df_tmp", _pdf)
        artifact_conn.execute(f"CREATE OR REPLACE TABLE {_quoted(_table_name)} AS SELECT * FROM _inquira_df_tmp")
        artifact_conn.unregister("_inquira_df_tmp")
        _row_count = int(artifact_conn.execute(f"SELECT COUNT(*) FROM {_quoted(_table_name)}").fetchone()[0])
        _preview_df = artifact_conn.execute(f"SELECT * FROM {_quoted(_table_name)} LIMIT 1000").fetchdf()
        _columns = [str(c) for c in list(_preview_df.columns)]
        _preview = _json.loads(_preview_df.to_json(orient="records", date_format="iso"))
        _inquira_df_artifacts[_name] = {
            "artifact_id": _artifact_id,
            "table_name": _table_name,
            "row_count": _row_count,
            "columns": _columns,
        }
        _bundle["dataframes"][_name] = {
            "artifact_id": _artifact_id,
            "row_count": _row_count,
            "columns": _columns,
            "data": _preview,
        }
        continue

    if _is_figure(_value):
        _seen_fig_names.add(_name)
        _artifact = _inquira_fig_artifacts.get(_name, {})
        _artifact_id = _artifact.get("artifact_id") or str(_uuid.uuid4())
        if _go is not None and isinstance(_value, _go.Figure):
            _fig_payload = _value.to_plotly_json()
        else:
            _fig_payload = _value
        _inquira_fig_artifacts[_name] = {"artifact_id": _artifact_id}
        _bundle["figures"][_name] = _fig_payload

for _stale_name in list(_inquira_df_artifacts.keys()):
    if _stale_name in _seen_df_names:
        continue
    _stale = _inquira_df_artifacts.pop(_stale_name, None)
    if _stale and "table_name" in _stale and "artifact_conn" in globals() and artifact_conn is not None:
        try:
            artifact_conn.execute(f"DROP TABLE IF EXISTS {_quoted(_stale['table_name'])}")
        except Exception:
            pass

for _stale_name in list(_inquira_fig_artifacts.keys()):
    if _stale_name not in _seen_fig_names:
        _inquira_fig_artifacts.pop(_stale_name, None)

_bundle
"""


@dataclass
class WorkspaceKernelSession:
    """Mutable state for a live workspace kernel."""

    workspace_id: str
    workspace_duckdb_path: str
    manager: AsyncKernelManager
    client: Any
    artifact_db_path: str
    status: str = "starting"
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))
    restart_count: int = 0
    bootstrap_completed: bool = False
    artifact_registry: dict[str, dict[str, Any]] = field(default_factory=dict)


class WorkspaceKernelManager:
    """Manage one persistent Python kernel per workspace ID."""

    def __init__(self, *, idle_minutes: int = 30) -> None:
        self._sessions: dict[str, WorkspaceKernelSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._idle_delta = timedelta(minutes=max(1, idle_minutes))

    async def execute(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        code: str,
        timeout: int,
        config: Any,
    ) -> dict[str, Any]:
        """Execute code in the workspace kernel and return legacy response payload."""
        try:
            session = await self._get_or_start_session(
                workspace_id=workspace_id,
                workspace_duckdb_path=workspace_duckdb_path,
                config=config,
            )
        except Exception as exc:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "error": str(exc),
                "result": None,
                "result_type": None,
            }

        async with session.lock:
            session.status = "busy"
            session.last_used = datetime.now(UTC)
            try:
                response = await asyncio.wait_for(
                    self._execute_on_session(session, code),
                    timeout=max(1, int(timeout)),
                )
                session.status = "ready"
                return response
            except asyncio.TimeoutError:
                await self._interrupt_or_restart(session, config=config)
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": f"Execution timed out after {timeout} seconds.",
                    "result": None,
                    "result_type": None,
                }
            except Exception as exc:
                session.status = "error"
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": str(exc),
                    "error": str(exc),
                    "result": None,
                    "result_type": None,
                }
            finally:
                session.last_used = datetime.now(UTC)

    async def reset_workspace(self, workspace_id: str) -> bool:
        """Shutdown and remove workspace kernel if present."""
        async with self._sessions_lock:
            session = self._sessions.pop(workspace_id, None)
        if session is None:
            return False
        await self._shutdown_session(session)
        return True

    async def get_status(self, workspace_id: str) -> str:
        """Return workspace kernel status."""
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return "missing"
        return session.status

    async def get_dataframe_rows(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any] | None:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return None

        artifact = session.artifact_registry.get(artifact_id)
        if artifact is None or artifact.get("kind") != "dataframe":
            return None

        table_name = str(artifact.get("table_name") or "")
        if not table_name:
            return None

        safe_limit = max(1, min(1000, int(limit)))
        safe_offset = max(0, int(offset))
        escaped = table_name.replace('"', '""')
        quoted = f'"{escaped}"'
        query = f"SELECT * FROM {quoted} LIMIT ? OFFSET ?"

        rows_df = await asyncio.to_thread(
            self._read_dataframe_page,
            session.artifact_db_path,
            query,
            safe_limit,
            safe_offset,
        )
        data = json.loads(rows_df.to_json(orient="records", date_format="iso"))
        return {
            "artifact_id": artifact_id,
            "name": artifact.get("name"),
            "row_count": int(artifact.get("row_count") or 0),
            "columns": [str(c) for c in list(rows_df.columns)],
            "rows": data,
            "offset": safe_offset,
            "limit": safe_limit,
        }

    async def shutdown(self) -> None:
        """Shutdown all active kernels and clear session cache."""
        async with self._sessions_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await self._shutdown_session(session)

    async def prune_idle_sessions(self) -> None:
        """Shutdown kernels that have been idle longer than the configured threshold."""
        cutoff = datetime.now(UTC) - self._idle_delta
        async with self._sessions_lock:
            stale_ids = [
                workspace_id
                for workspace_id, session in self._sessions.items()
                if session.last_used < cutoff and not session.lock.locked()
            ]
            stale_sessions = [self._sessions.pop(workspace_id) for workspace_id in stale_ids]
        for session in stale_sessions:
            await self._shutdown_session(session)

    async def _get_or_start_session(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        config: Any,
    ) -> WorkspaceKernelSession:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
            if session is None:
                session = await self._start_session(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    config=config,
                )
                self._sessions[workspace_id] = session
            elif session.workspace_duckdb_path != workspace_duckdb_path:
                await self._shutdown_session(session)
                session = await self._start_session(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    config=config,
                )
                self._sessions[workspace_id] = session
        return session

    async def _start_session(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        config: Any,
    ) -> WorkspaceKernelSession:
        ensure_runner_kernel_dependencies(config)
        runner_python = resolve_runner_python(config)
        km = AsyncKernelManager(kernel_name="python3")
        kernel_spec = km.kernel_spec
        if kernel_spec is None:
            raise RuntimeError("Failed to load Jupyter kernelspec for python3.")
        kernel_spec.argv = [
            runner_python,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        await km.start_kernel()
        kc = km.client()
        kc.start_channels()
        await kc.wait_for_ready(timeout=max(5, int(config.runner_policy.timeout_seconds)))
        session = WorkspaceKernelSession(
            workspace_id=workspace_id,
            workspace_duckdb_path=workspace_duckdb_path,
            manager=km,
            client=kc,
            artifact_db_path=str(Path(workspace_duckdb_path).with_name("workspace_runtime_artifacts.duckdb")),
            status="ready",
        )
        await self._bootstrap_workspace(session)
        return session

    async def _bootstrap_workspace(self, session: WorkspaceKernelSession) -> None:
        duckdb_path = Path(session.workspace_duckdb_path).as_posix()
        bootstrap_code = (
            "import duckdb\n"
            f"conn = duckdb.connect(r'''{duckdb_path}''', read_only=True)\n"
            f"artifact_conn = duckdb.connect(r'''{session.artifact_db_path}''', read_only=False)\n"
        )
        output = await self._execute_on_session(session, bootstrap_code)
        if output.get("success"):
            session.bootstrap_completed = True
            return
        raise RuntimeError(output.get("error") or "Workspace kernel bootstrap failed")

    async def _execute_on_session(
        self,
        session: WorkspaceKernelSession,
        code: str,
    ) -> dict[str, Any]:
        parsed = await self._execute_request(session, code)

        if (
            parsed.result is None
            and parsed.error is None
            and not parsed.stderr_parts
        ):
            probe = await self._execute_request(session, _FALLBACK_RESULT_PROBE_CODE)
            if probe.result is not None and probe.result_type is not None:
                parsed.result = probe.result
                parsed.result_type = probe.result_type

        variables = {"dataframes": {}, "figures": {}, "scalars": {}}
        if session.bootstrap_completed and parsed.error is None:
            try:
                artifact_probe = await self._execute_request(session, _ARTIFACT_SYNC_CODE)
                bundle = self._coerce_variable_bundle(artifact_probe.result)
                variables = bundle
                self._update_artifact_registry(session, bundle)
            except Exception:
                variables = {"dataframes": {}, "figures": {}, "scalars": {}}

        response = parsed.as_response()
        response["variables"] = variables
        return response

    async def _execute_request(
        self,
        session: WorkspaceKernelSession,
        code: str,
    ) -> ParsedExecutionOutput:
        msg_id = session.client.execute(code, store_history=True, stop_on_error=True)
        parsed = ParsedExecutionOutput()

        while True:
            msg = await session.client.get_iopub_msg(timeout=1)
            parent_id = (
                msg.get("parent_header", {}).get("msg_id")
                if isinstance(msg, dict)
                else None
            )
            if parent_id != msg_id:
                continue
            msg_type = str(msg.get("msg_type", ""))
            content = msg.get("content", {})
            if msg_type == "status" and content.get("execution_state") == "idle":
                break
            if isinstance(content, dict):
                update_from_iopub_message(parsed, msg_type, content)

        return parsed

    async def _interrupt_or_restart(self, session: WorkspaceKernelSession, config: Any) -> None:
        await self._await_maybe(session.manager.interrupt_kernel())
        try:
            await asyncio.wait_for(
                session.client.wait_for_ready(timeout=2),
                timeout=3,
            )
            session.status = "ready"
            return
        except Exception:
            await self._await_maybe(session.manager.restart_kernel(now=True))
            await session.client.wait_for_ready(timeout=max(5, int(config.runner_policy.timeout_seconds)))
            await self._bootstrap_workspace(session)
            session.restart_count += 1
            session.status = "ready"

    async def _shutdown_session(self, session: WorkspaceKernelSession) -> None:
        try:
            session.client.stop_channels()
        except Exception:
            pass
        await self._await_maybe(session.manager.shutdown_kernel(now=True))

    async def _await_maybe(self, maybe_awaitable: Any) -> None:
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    @staticmethod
    def _coerce_variable_bundle(result: Any) -> dict[str, dict[str, Any]]:
        default_bundle = {"dataframes": {}, "figures": {}, "scalars": {}}
        if not isinstance(result, dict):
            return default_bundle
        dataframes = result.get("dataframes")
        figures = result.get("figures")
        scalars = result.get("scalars")
        if not isinstance(dataframes, dict):
            dataframes = {}
        if not isinstance(figures, dict):
            figures = {}
        if not isinstance(scalars, dict):
            scalars = {}
        return {
            "dataframes": dataframes,
            "figures": figures,
            "scalars": scalars,
        }

    @staticmethod
    def _update_artifact_registry(
        session: WorkspaceKernelSession,
        bundle: dict[str, dict[str, Any]],
    ) -> None:
        registry: dict[str, dict[str, Any]] = {}

        for name, value in bundle.get("dataframes", {}).items():
            if not isinstance(value, dict):
                continue
            artifact_id = value.get("artifact_id")
            if artifact_id is None:
                continue
            registry[str(artifact_id)] = {
                "kind": "dataframe",
                "name": str(name),
                "table_name": f"df_{WorkspaceKernelManager._sanitize_table_suffix(name)}",
                "row_count": int(value.get("row_count") or 0),
            }

        for name, value in bundle.get("figures", {}).items():
            if not isinstance(value, dict):
                continue
            artifact_id = value.get("artifact_id")
            if artifact_id is None:
                continue
            registry[str(artifact_id)] = {
                "kind": "figure",
                "name": str(name),
            }

        session.artifact_registry = registry

    @staticmethod
    def _sanitize_table_suffix(value: Any) -> str:
        raw = str(value)
        cleaned = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in raw)
        if not cleaned:
            return "value"
        return cleaned[:96]

    @staticmethod
    def _read_dataframe_page(
        db_path: str,
        query: str,
        limit: int,
        offset: int,
    ) -> Any:
        conn = duckdb.connect(db_path, read_only=True)
        try:
            return conn.execute(query, [limit, offset]).fetchdf()
        finally:
            conn.close()
