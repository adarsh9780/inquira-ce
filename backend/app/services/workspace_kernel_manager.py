"""Workspace-scoped Jupyter kernel lifecycle and execution orchestration."""

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

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

_EXPORTS_PROBE_CODE = """
_inquira_get_active_exports()
"""

_RUN_EXPORTS_PROBE_TEMPLATE = """
_inquira_get_active_exports(run_id={run_id!r})
"""

_KERNEL_RESOURCE_CLEANUP_CODE = """
try:
    if "scratchpad_conn" in globals() and scratchpad_conn is not None:
        scratchpad_conn.close()
except Exception:
    pass

try:
    if "conn" in globals() and conn is not None:
        conn.close()
except Exception:
    pass

None
"""


@dataclass
class WorkspaceKernelSession:
    """Mutable state for a live workspace kernel."""

    workspace_id: str
    workspace_duckdb_path: str
    manager: AsyncKernelManager
    client: Any
    scratchpad_db_path: str
    status: str = "starting"
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))
    restart_count: int = 0
    bootstrap_completed: bool = False


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
                "has_stdout": False,
                "has_stderr": True,
                "error": str(exc),
                "result": None,
                "result_type": None,
                "result_kind": "error",
                "result_name": None,
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
                    "has_stdout": False,
                    "has_stderr": False,
                    "error": f"Execution timed out after {timeout} seconds.",
                    "result": None,
                    "result_type": None,
                    "result_kind": "error",
                    "result_name": None,
                }
            except Exception as exc:
                session.status = "error"
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": str(exc),
                    "has_stdout": False,
                    "has_stderr": True,
                    "error": str(exc),
                    "result": None,
                    "result_type": None,
                    "result_kind": "error",
                    "result_name": None,
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

    async def interrupt_workspace(self, workspace_id: str) -> bool:
        """Interrupt a running workspace kernel if present."""
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return False
        try:
            await self._await_maybe(session.manager.interrupt_kernel())
            session.status = "ready"
            session.last_used = datetime.now(UTC)
            return True
        except Exception:
            session.status = "error"
            return False

    async def get_run_exports(
        self,
        *,
        workspace_id: str,
        run_id: str,
    ) -> list[dict[str, Any]]:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return []
        probe_code = _RUN_EXPORTS_PROBE_TEMPLATE.format(run_id=str(run_id))
        async with session.lock:
            session.last_used = datetime.now(UTC)
            parsed = await self._execute_request(session, probe_code)
        if parsed.error is not None or not isinstance(parsed.result, list):
            return []
        return [item for item in parsed.result if isinstance(item, dict)]

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

        safe_limit = max(1, min(1000, int(limit)))
        safe_offset = max(0, int(offset))
        escaped_artifact_id = str(artifact_id).replace("'", "''")
        page_code = (
            "import json as _json\n"
            f"_art = scratchpad_conn.execute(\"SELECT logical_name, table_name FROM artifact_manifest WHERE artifact_id = '{escaped_artifact_id}' AND kind = 'dataframe' LIMIT 1\").fetchone()\n"
            "if _art is None:\n"
            "    _page = None\n"
            "else:\n"
            "    _name, _table_name = _art\n"
            "    _escaped = str(_table_name).replace('\"', '\"\"')\n"
            f"    _rows_df = scratchpad_conn.execute(f'SELECT * FROM \"{{_escaped}}\" LIMIT {safe_limit} OFFSET {safe_offset}').fetchdf()\n"
            "    _count = int(scratchpad_conn.execute(f'SELECT COUNT(*) FROM \"{_escaped}\"').fetchone()[0])\n"
            "    _page = {\n"
            f"      'artifact_id': '{escaped_artifact_id}',\n"
            "      'name': str(_name),\n"
            "      'row_count': _count,\n"
            "      'columns': [str(c) for c in list(_rows_df.columns)],\n"
            "      'rows': _json.loads(_rows_df.to_json(orient='records', date_format='iso')),\n"
            f"      'offset': {safe_offset},\n"
            f"      'limit': {safe_limit},\n"
            "    }\n"
            "_page\n"
        )

        async with session.lock:
            session.last_used = datetime.now(UTC)
            parsed = await self._execute_request(session, page_code)

        if parsed.error is not None or parsed.result is None:
            return None
        if not isinstance(parsed.result, dict):
            return None
        return parsed.result

    async def ensure_ready(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        config: Any,
        progress_callback: Any | None = None,
    ) -> bool:
        """Ensure workspace kernel session is running and bootstrapped."""
        await self._get_or_start_session(
            workspace_id=workspace_id,
            workspace_duckdb_path=workspace_duckdb_path,
            config=config,
            progress_callback=progress_callback,
        )
        return True

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
        progress_callback: Any | None = None,
    ) -> WorkspaceKernelSession:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
            if session is None:
                session = await self._start_session_compat(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    config=config,
                    progress_callback=progress_callback,
                )
                self._sessions[workspace_id] = session
            elif session.workspace_duckdb_path != workspace_duckdb_path:
                await self._shutdown_session(session)
                session = await self._start_session_compat(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    config=config,
                    progress_callback=progress_callback,
                )
                self._sessions[workspace_id] = session
        return session

    async def _start_session_compat(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        config: Any,
        progress_callback: Any | None = None,
    ) -> WorkspaceKernelSession:
        """Call `_start_session` with optional progress callback when supported."""
        start_params = inspect.signature(self._start_session).parameters
        kwargs: dict[str, Any] = {
            "workspace_id": workspace_id,
            "workspace_duckdb_path": workspace_duckdb_path,
            "config": config,
        }
        if "progress_callback" in start_params:
            kwargs["progress_callback"] = progress_callback
        return await self._start_session(**kwargs)

    async def _start_session(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        config: Any,
        progress_callback: Any | None = None,
    ) -> WorkspaceKernelSession:
        if progress_callback is not None:
            await self._await_maybe(progress_callback("workspace_runtime_env", "Preparing workspace virtual environment..."))
        env_status = ensure_runner_kernel_dependencies(config, workspace_duckdb_path)
        if progress_callback is not None:
            if env_status.created:
                await self._await_maybe(progress_callback("workspace_runtime_env", f"Created virtual environment at {env_status.venv_path}"))
            if env_status.packages_installed:
                await self._await_maybe(progress_callback("workspace_runtime_packages", "Installing workspace data-science packages..."))
            else:
                await self._await_maybe(progress_callback("workspace_runtime_packages", "Workspace packages already up to date."))
        runner_python = resolve_runner_python(config, workspace_duckdb_path)
        if progress_callback is not None:
            await self._await_maybe(progress_callback("workspace_runtime_kernel", "Starting Python kernel..."))
        km = AsyncKernelManager(kernel_name="python3")
        kc = None
        ready_timeout = max(15, int(config.runner_policy.timeout_seconds) * 2)
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
        try:
            await km.start_kernel()
            kc = km.client()
            kc.start_channels()
            await kc.wait_for_ready(timeout=ready_timeout)
            session = WorkspaceKernelSession(
                workspace_id=workspace_id,
                workspace_duckdb_path=workspace_duckdb_path,
                manager=km,
                client=kc,
                scratchpad_db_path=str(Path(workspace_duckdb_path).parent / "scratchpad" / "artifacts.duckdb"),
                status="ready",
            )
            if progress_callback is not None:
                await self._await_maybe(progress_callback("workspace_runtime_bootstrap", "Warming workspace runtime..."))
            await self._bootstrap_workspace(session)
            return session
        except asyncio.TimeoutError as exc:
            await self._shutdown_partial_startup(km, kc)
            raise RuntimeError(
                f"Timed out waiting for workspace kernel to become ready after {ready_timeout} seconds."
            ) from exc
        except Exception as exc:
            await self._shutdown_partial_startup(km, kc)
            raise RuntimeError(f"Failed to start workspace kernel: {self._describe_exception(exc)}") from exc

    async def _bootstrap_workspace(self, session: WorkspaceKernelSession) -> None:
        duckdb_path = Path(session.workspace_duckdb_path).as_posix()
        scratchpad_file = Path(session.scratchpad_db_path)
        scratchpad_file.parent.mkdir(parents=True, exist_ok=True)
        scratchpad_path = scratchpad_file.as_posix()
        bootstrap_code = (
            "import duckdb\n"
            "import json as _json\n"
            "import uuid as _uuid\n"
            "from datetime import datetime as _dt, timedelta as _td, timezone as _tz\n"
            f"conn = duckdb.connect(r'''{duckdb_path}''', read_only=True)\n"
            f"scratchpad_conn = duckdb.connect(r'''{scratchpad_path}''', read_only=False)\n"
            "scratchpad_conn.execute(\"\"\"\n"
            "CREATE TABLE IF NOT EXISTS artifact_manifest (\n"
            "  artifact_id VARCHAR PRIMARY KEY,\n"
            "  run_id VARCHAR NOT NULL,\n"
            "  workspace_id VARCHAR NOT NULL,\n"
            "  logical_name VARCHAR NOT NULL,\n"
            "  kind VARCHAR NOT NULL,\n"
            "  table_name VARCHAR,\n"
            "  payload_json TEXT,\n"
            "  schema_json TEXT,\n"
            "  row_count BIGINT,\n"
            "  created_at TIMESTAMP NOT NULL,\n"
            "  expires_at TIMESTAMP NOT NULL,\n"
            "  status VARCHAR NOT NULL,\n"
            "  error TEXT\n"
            ")\n"
            "\"\"\")\n"
            "scratchpad_conn.execute(\"\"\"\n"
            "CREATE TABLE IF NOT EXISTS run_manifest (\n"
            "  run_id VARCHAR PRIMARY KEY,\n"
            "  workspace_id VARCHAR NOT NULL,\n"
            "  conversation_id VARCHAR,\n"
            "  turn_id VARCHAR,\n"
            "  question TEXT,\n"
            "  generated_code TEXT,\n"
            "  executed_code TEXT,\n"
            "  stdout TEXT,\n"
            "  stderr TEXT,\n"
            "  execution_status VARCHAR NOT NULL,\n"
            "  retry_count INTEGER NOT NULL,\n"
            "  created_at TIMESTAMP NOT NULL,\n"
            "  expires_at TIMESTAMP NOT NULL\n"
            ")\n"
            "\"\"\")\n"
            "if \"_inquira_run_exports\" not in globals():\n"
            "    _inquira_run_exports = {}\n"
            "if \"_inquira_active_run_id\" not in globals():\n"
            "    _inquira_active_run_id = None\n"
            "if \"_inquira_workspace_id\" not in globals():\n"
            f"    _inquira_workspace_id = {session.workspace_id!r}\n"
            "if \"_inquira_ttl_hours\" not in globals():\n"
            "    _inquira_ttl_hours = 48\n"
            "def _inquira_safe_name(name):\n"
            "    cleaned = ''.join(ch if (str(ch).isalnum() or str(ch) == '_') else '_' for ch in str(name or 'artifact'))\n"
            "    return (cleaned[:96] or 'artifact')\n"
            "def _inquira_now_and_expiry():\n"
            "    now = _dt.now(_tz.utc)\n"
            "    return now, now + _td(hours=max(1, int(_inquira_ttl_hours)))\n"
            "def set_active_run(run_id):\n"
            "    global _inquira_active_run_id\n"
            "    _inquira_active_run_id = str(run_id)\n"
            "    if _inquira_active_run_id not in _inquira_run_exports:\n"
            "        _inquira_run_exports[_inquira_active_run_id] = []\n"
            "    return _inquira_active_run_id\n"
            "def _inquira_get_active_exports(run_id=None):\n"
            "    key = str(run_id or _inquira_active_run_id or '')\n"
            "    return list(_inquira_run_exports.get(key, []))\n"
            "def _inquira_export_envelope(*, artifact_id, run_id, kind, logical_name, table_name=None, row_count=None, schema=None, preview_rows=None, status='ready', error=None):\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    return {\n"
            "      'artifact_id': str(artifact_id),\n"
            "      'run_id': str(run_id),\n"
            "      'kind': str(kind),\n"
            "      'pointer': f'duckdb://scratchpad/artifacts.duckdb#artifact={artifact_id}',\n"
            "      'logical_name': str(logical_name),\n"
            "      'row_count': int(row_count) if row_count is not None else None,\n"
            "      'schema': schema,\n"
            "      'preview_rows': preview_rows or [],\n"
            "      'created_at': now.isoformat(),\n"
            "      'expires_at': expires.isoformat(),\n"
            "      'status': status,\n"
            "      'error': error,\n"
            "      'table_name': table_name,\n"
            "    }\n"
            "def export_dataframe(df, logical_name, run_id=None, title=None, insight=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No active run_id set. Call set_active_run(run_id) first.')\n"
            "    import pandas as _pd\n"
            "    try:\n"
            "        import polars as _pl\n"
            "    except Exception:\n"
            "        _pl = None\n"
            "    if _pl is not None and isinstance(df, _pl.LazyFrame):\n"
            "        df = df.collect()\n"
            "    if _pl is not None and isinstance(df, _pl.DataFrame):\n"
            "        pdf = df.to_pandas()\n"
            "    elif isinstance(df, _pd.DataFrame):\n"
            "        pdf = df\n"
            "    else:\n"
            "        pdf = _pd.DataFrame(df)\n"
            "    seq = len(_inquira_run_exports.get(active_run, [])) + 1\n"
            "    run_short = ''.join(ch for ch in active_run if ch.isalnum())[:12] or 'run'\n"
            "    table_name = f'art_{run_short}_{seq}'\n"
            "    artifact_id = str(_uuid.uuid4())\n"
            "    scratchpad_conn.register('_inquira_df_tmp', pdf)\n"
            "    scratchpad_conn.execute(f'CREATE TABLE {table_name} AS SELECT * FROM _inquira_df_tmp')\n"
            "    scratchpad_conn.unregister('_inquira_df_tmp')\n"
            "    row_count = int(scratchpad_conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0])\n"
            "    preview_df = scratchpad_conn.execute(f'SELECT * FROM {table_name} LIMIT 50').fetchdf()\n"
            "    schema = [{'name': str(c), 'dtype': str(t)} for c, t in zip(list(preview_df.columns), list(preview_df.dtypes))]\n"
            "    preview_rows = _json.loads(preview_df.to_json(orient='records', date_format='iso'))\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    payload = _json.dumps({'title': title, 'insight': insight}, default=str)\n"
            "    scratchpad_conn.execute(\n"
            "      'INSERT INTO artifact_manifest (artifact_id, run_id, workspace_id, logical_name, kind, table_name, payload_json, schema_json, row_count, created_at, expires_at, status, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',\n"
            "      [artifact_id, active_run, _inquira_workspace_id, str(logical_name), 'dataframe', table_name, payload, _json.dumps(schema), row_count, now, expires, 'ready', None]\n"
            "    )\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='dataframe', logical_name=str(logical_name), table_name=table_name, row_count=row_count, schema=schema, preview_rows=preview_rows)\n"
            "    _inquira_run_exports.setdefault(active_run, []).append(envelope)\n"
            "    return envelope\n"
            "def export_figure(fig, logical_name, run_id=None, title=None, insight=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No active run_id set. Call set_active_run(run_id) first.')\n"
            "    try:\n"
            "        import plotly.graph_objects as _go\n"
            "    except Exception:\n"
            "        _go = None\n"
            "    if _go is not None and isinstance(fig, _go.Figure):\n"
            "        fig_payload = _json.loads(fig.to_json())\n"
            "    else:\n"
            "        fig_payload = _json.loads(_json.dumps(fig, default=str))\n"
            "    artifact_id = str(_uuid.uuid4())\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    payload = _json.dumps({'figure': fig_payload, 'title': title, 'insight': insight}, default=str)\n"
            "    scratchpad_conn.execute(\n"
            "      'INSERT INTO artifact_manifest (artifact_id, run_id, workspace_id, logical_name, kind, table_name, payload_json, schema_json, row_count, created_at, expires_at, status, error) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, ?, ?, ?, ?)',\n"
            "      [artifact_id, active_run, _inquira_workspace_id, str(logical_name), 'figure', payload, now, expires, 'ready', None]\n"
            "    )\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='figure', logical_name=str(logical_name), preview_rows=[])\n"
            "    _inquira_run_exports.setdefault(active_run, []).append(envelope)\n"
            "    return envelope\n"
            "def export_scalar(value, logical_name, run_id=None, meta=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No active run_id set. Call set_active_run(run_id) first.')\n"
            "    artifact_id = str(_uuid.uuid4())\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    payload = _json.dumps({'value': value, 'meta': meta}, default=str)\n"
            "    scratchpad_conn.execute(\n"
            "      'INSERT INTO artifact_manifest (artifact_id, run_id, workspace_id, logical_name, kind, table_name, payload_json, schema_json, row_count, created_at, expires_at, status, error) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, ?, ?, ?, ?)',\n"
            "      [artifact_id, active_run, _inquira_workspace_id, str(logical_name), 'scalar', payload, now, expires, 'ready', None]\n"
            "    )\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='scalar', logical_name=str(logical_name), preview_rows=[])\n"
            "    _inquira_run_exports.setdefault(active_run, []).append(envelope)\n"
            "    return envelope\n"
            "def finalize_run(run_id, metadata=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No run_id provided to finalize_run')\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    payload = metadata or {}\n"
            "    scratchpad_conn.execute(\n"
            "      'INSERT OR REPLACE INTO run_manifest (run_id, workspace_id, conversation_id, turn_id, question, generated_code, executed_code, stdout, stderr, execution_status, retry_count, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',\n"
            "      [active_run, _inquira_workspace_id, None, None, str(payload.get('question') or ''), str(payload.get('generated_code') or ''), str(payload.get('executed_code') or ''), str(payload.get('stdout') or ''), str(payload.get('stderr') or ''), str(payload.get('execution_status') or 'completed'), int(payload.get('retry_count') or 0), now, expires]\n"
            "    )\n"
            "    return {'run_id': active_run, 'exports': list(_inquira_run_exports.get(active_run, []))}\n"
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

        should_probe_fallback = (
            parsed.error is None
            and (
                parsed.result is None
                or parsed.result_type in {None, "scalar"}
            )
        )

        if should_probe_fallback:
            probe = await self._execute_request(session, _FALLBACK_RESULT_PROBE_CODE)
            if (
                probe.result is not None
                and probe.result_type in {"DataFrame", "Figure"}
            ):
                parsed.result = probe.result
                parsed.result_type = probe.result_type
            elif (
                parsed.result is None
                and probe.result is not None
                and probe.result_type is not None
            ):
                parsed.result = probe.result
                parsed.result_type = probe.result_type

        variables: dict[str, dict[str, Any]] = {"dataframes": {}, "figures": {}, "scalars": {}}
        artifacts: list[dict[str, Any]] = []
        if session.bootstrap_completed and parsed.error is None:
            try:
                exports_probe = await self._execute_request(session, _EXPORTS_PROBE_CODE)
                if isinstance(exports_probe.result, list):
                    artifacts = [item for item in exports_probe.result if isinstance(item, dict)]
            except Exception:
                artifacts = []

        response = parsed.as_response()
        response["variables"] = variables
        response["artifacts"] = artifacts
        result_kind, result_name = self._resolve_canonical_result(
            code=code,
            parsed=parsed,
            variables=variables,
        )
        response["result_kind"] = result_kind
        response["result_name"] = result_name
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
            async with session.lock:
                await asyncio.wait_for(
                    self._execute_request(session, _KERNEL_RESOURCE_CLEANUP_CODE),
                    timeout=2,
                )
        except Exception:
            # Best-effort cleanup: continue with forced kernel shutdown.
            pass
        try:
            session.client.stop_channels()
        except Exception:
            pass
        await self._await_maybe(session.manager.shutdown_kernel(now=True))

    async def _await_maybe(self, maybe_awaitable: Any) -> None:
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    async def _shutdown_partial_startup(self, manager: Any, client: Any) -> None:
        try:
            if client is not None:
                client.stop_channels()
        except Exception:
            pass
        try:
            if manager is not None:
                await self._await_maybe(manager.shutdown_kernel(now=True))
        except Exception:
            pass

    @staticmethod
    def _describe_exception(exc: Exception) -> str:
        text = str(exc).strip()
        if text:
            return text
        return exc.__class__.__name__

    @staticmethod
    def _extract_identifier_reference(code: str) -> str | None:
        trimmed = str(code or "").strip()
        if not trimmed:
            return None
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", trimmed):
            return trimmed
        return None

    @staticmethod
    def _normalize_result_kind(result_type: str | None) -> str:
        normalized = str(result_type or "").strip().lower()
        if normalized == "dataframe":
            return "dataframe"
        if normalized == "figure":
            return "figure"
        if normalized == "scalar":
            return "scalar"
        return "none"

    @classmethod
    def _resolve_canonical_result(
        cls,
        *,
        code: str,
        parsed: ParsedExecutionOutput,
        variables: dict[str, dict[str, Any]],
    ) -> tuple[str, str | None]:
        if parsed.error:
            return "error", None

        identifier_ref = cls._extract_identifier_reference(code)
        if identifier_ref:
            if identifier_ref in variables.get("dataframes", {}):
                return "dataframe", identifier_ref
            if identifier_ref in variables.get("figures", {}):
                return "figure", identifier_ref
            if identifier_ref in variables.get("scalars", {}):
                return "scalar", identifier_ref

        kind = cls._normalize_result_kind(parsed.result_type)
        if kind in {"dataframe", "figure", "scalar"}:
            return kind, None
        if parsed.result is not None:
            return "scalar", None
        return "none", None
