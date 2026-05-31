"""Workspace-scoped Jupyter kernel lifecycle and execution orchestration."""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Empty as QueueEmpty
from typing import Any

from jupyter_client import AsyncKernelManager

from app.data_access.coordinator import LeaseConflictError, LeaseKinds, ResourceLeaseCoordinator
from app.data_access.workspace_db import WorkspaceOfflineAdapter
from app.v1.db.session import AppDataSessionLocal
from app.services.jupyter_message_parser import (
    ParsedExecutionOutput,
    update_from_iopub_message,
)
from app.core.logger import logprint
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

def _build_identifier_result_probe_code(identifier: str) -> str:
    target = repr(str(identifier))
    return (
        "import json as _json\n"
        "try:\n"
        "    import pandas as _pd\n"
        "except Exception:\n"
        "    _pd = None\n"
        "try:\n"
        "    import plotly.graph_objects as _go\n"
        "except Exception:\n"
        "    _go = None\n"
        f"_inquira_identifier = {target}\n"
        "_inquira_target = globals().get(_inquira_identifier) if _inquira_identifier in globals() else None\n"
        "if _inquira_target is None:\n"
        "    _inquira_payload = None\n"
        "elif _pd is not None and isinstance(_inquira_target, _pd.DataFrame):\n"
        "    _preview = _inquira_target.head(1000)\n"
        "    _inquira_payload = {\n"
        "        'columns': [str(c) for c in list(_preview.columns)],\n"
        "        'data': _json.loads(_preview.to_json(orient='records', date_format='iso')),\n"
        "    }\n"
        "elif _go is not None and isinstance(_inquira_target, _go.Figure):\n"
        "    _inquira_payload = _inquira_target.to_plotly_json()\n"
        "else:\n"
        "    _inquira_payload = _inquira_target\n"
        "_inquira_payload\n"
    )

_KERNEL_RESOURCE_CLEANUP_CODE = """
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
    status: str = "starting"
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))
    restart_count: int = 0
    bootstrap_completed: bool = False
    runtime_lease_owner_token: str | None = None
    runtime_lease_expires_at: datetime | None = None
    runtime_lease_renew_after: datetime | None = None


class WorkspaceKernelManager:
    """Manage one persistent Python kernel per workspace ID."""

    def __init__(self, *, idle_minutes: int = 30) -> None:
        self._sessions: dict[str, WorkspaceKernelSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._idle_delta = timedelta(minutes=max(1, idle_minutes))
        self._runtime_lease_delta = timedelta(
            seconds=max(300, int(self._idle_delta.total_seconds()) + 120)
        )
        self._lease_coordinator = ResourceLeaseCoordinator(
            lease_seconds=int(self._runtime_lease_delta.total_seconds())
        )

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
            await self._touch_session(session)
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
            await self._touch_session(session)
            return True
        except Exception:
            session.status = "error"
            return False

    async def get_workspace_columns(
        self,
        *,
        workspace_id: str,
    ) -> list[dict[str, str]]:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return []

        probe_code = (
            "_rows = conn.execute(\"\"\"\n"
            "    SELECT table_name, column_name, data_type\n"
            "    FROM information_schema.columns\n"
            "    WHERE table_schema = 'main'\n"
            "    ORDER BY table_name, ordinal_position\n"
            "\"\"\").fetchall()\n"
            "[\n"
            "    {\n"
            "        'table_name': str(_row[0]),\n"
            "        'column_name': str(_row[1]),\n"
            "        'dtype': str(_row[2] or ''),\n"
            "    }\n"
            "    for _row in _rows\n"
            "]\n"
        )

        async with session.lock:
            await self._touch_session(session)
            parsed = await self._execute_request(session, probe_code)

        if parsed.error is not None or not isinstance(parsed.result, list):
            return []
        return [item for item in parsed.result if isinstance(item, dict)]

    async def get_workspace_table_schema(
        self,
        *,
        workspace_id: str,
        table_name: str,
        allow_sample_values: bool = False,
    ) -> list[dict[str, Any]] | None:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return None

        escaped_table = str(table_name).replace('"', '""')
        probe_code = (
            f"_table_name = {json.dumps(escaped_table, ensure_ascii=True)}\n"
            f"_allow_sample_values = {bool(allow_sample_values)!r}\n"
            "try:\n"
            "    _rows = conn.execute(f'DESCRIBE \"{_table_name}\"').fetchall()\n"
            "except Exception:\n"
            "    _result = None\n"
            "else:\n"
            "    _result = []\n"
            "    for _row in _rows:\n"
            "        _col_name = str(_row[0])\n"
            "        _samples = []\n"
            "        if _allow_sample_values:\n"
            "            _escaped_col = _col_name.replace('\"', '\"\"')\n"
            "            _sample_rows = conn.execute(\n"
            "                f'SELECT DISTINCT \"{_escaped_col}\" FROM \"{_table_name}\" LIMIT 10'\n"
            "            ).fetchall()\n"
            "            _samples = [_sample[0] for _sample in _sample_rows]\n"
            "        _result.append({\n"
            "            'name': _col_name,\n"
            "            'dtype': str(_row[1]),\n"
            "            'samples': _samples,\n"
            "            'description': '',\n"
            "            'aliases': [],\n"
            "        })\n"
            "_result\n"
        )

        async with session.lock:
            await self._touch_session(session)
            parsed = await self._execute_request(session, probe_code)

        if parsed.error is not None:
            return None
        if parsed.result is None or not isinstance(parsed.result, list):
            return None
        return [item for item in parsed.result if isinstance(item, dict)]

    async def ingest_dataset(
        self,
        *,
        workspace_id: str,
        source_path: str,
        table_name: str,
        file_type: str,
    ) -> dict[str, Any] | None:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return None

        escaped_table = str(table_name).replace('"', '""')
        ingest_code = (
            "import duckdb as _duckdb\n"
            f"_source = {json.dumps(str(source_path), ensure_ascii=True)}\n"
            f"_table_name = {json.dumps(escaped_table, ensure_ascii=True)}\n"
            f"_duckdb_path = {json.dumps(str(session.workspace_duckdb_path), ensure_ascii=True)}\n"
            f"_file_type = {json.dumps(str(file_type), ensure_ascii=True)}\n"
            "_result = None\n"
            "try:\n"
            "    try:\n"
            "        if 'conn' in globals() and conn is not None:\n"
            "            conn.close()\n"
            "    except Exception:\n"
            "        pass\n"
            "    conn = _duckdb.connect(_duckdb_path, read_only=False)\n"
            "    if _file_type in {'csv', 'tsv'}:\n"
            "        conn.execute(\n"
            "            f'CREATE OR REPLACE TABLE \"{_table_name}\" AS SELECT * FROM read_csv_auto(?)',\n"
            "            [_source],\n"
            "        )\n"
            "    elif _file_type == 'parquet':\n"
            "        conn.execute(\n"
            "            f'CREATE OR REPLACE TABLE \"{_table_name}\" AS SELECT * FROM read_parquet(?)',\n"
            "            [_source],\n"
            "        )\n"
            "    elif _file_type == 'json':\n"
            "        conn.execute(\n"
            "            f'CREATE OR REPLACE TABLE \"{_table_name}\" AS SELECT * FROM read_json_auto(?)',\n"
            "            [_source],\n"
            "        )\n"
            "    elif _file_type in {'xlsx', 'xls'}:\n"
            "        import pandas as _pd\n"
            "        _excel_df = _pd.read_excel(_source, engine='openpyxl')\n"
            "        conn.register('_inquira_excel_df', _excel_df)\n"
            "        try:\n"
            "            conn.execute(\n"
            "                f'CREATE OR REPLACE TABLE \"{_table_name}\" AS SELECT * FROM _inquira_excel_df'\n"
            "            )\n"
            "        finally:\n"
            "            try:\n"
            "                conn.unregister('_inquira_excel_df')\n"
            "            except Exception:\n"
            "                pass\n"
            "    else:\n"
            "        raise RuntimeError(f'Unsupported file type: {_file_type}')\n"
            "    _row_count = int(conn.execute(f'SELECT COUNT(*) FROM \"{_table_name}\"').fetchone()[0])\n"
            "    _schema_rows = conn.execute(f'DESCRIBE \"{_table_name}\"').fetchall()\n"
            "    _result = {\n"
            "        'row_count': _row_count,\n"
            "        'columns': [\n"
            "            {\n"
            "                'name': str(_row[0]),\n"
            "                'dtype': str(_row[1]),\n"
            "                'description': '',\n"
            "                'samples': [],\n"
            "            }\n"
            "            for _row in _schema_rows\n"
            "        ],\n"
            "    }\n"
            "finally:\n"
            "    try:\n"
            "        if 'conn' in globals() and conn is not None:\n"
            "            conn.close()\n"
            "    except Exception:\n"
            "        pass\n"
            "    conn = _duckdb.connect(_duckdb_path, read_only=True)\n"
            "_result\n"
        )

        async with session.lock:
            await self._touch_session(session)
            parsed = await self._execute_request(
                session,
                ingest_code,
                iopub_idle_timeout=300.0,
            )

        if parsed.error is not None:
            message = str(parsed.error).strip().splitlines()[-1].strip()
            raise RuntimeError(message or "Dataset import failed in workspace kernel.")
        if not isinstance(parsed.result, dict):
            raise RuntimeError("Dataset import failed in workspace kernel.")
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
        session: WorkspaceKernelSession | None = None
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
                status="ready",
                runtime_lease_owner_token=f"kernel:{workspace_id}:{uuid.uuid4()}",
            )
            await self._acquire_runtime_lease(session)
            if progress_callback is not None:
                await self._await_maybe(progress_callback("workspace_runtime_bootstrap", "Warming workspace runtime..."))
            await self._bootstrap_workspace(session)
            return session
        except asyncio.TimeoutError as exc:
            await self._shutdown_partial_startup(km, kc)
            if session is not None:
                await self._release_runtime_lease(session)
            raise RuntimeError(
                f"Timed out waiting for workspace kernel to become ready after {ready_timeout} seconds."
            ) from exc
        except Exception as exc:
            await self._shutdown_partial_startup(km, kc)
            if session is not None:
                await self._release_runtime_lease(session)
            raise RuntimeError(f"Failed to start workspace kernel: {self._describe_exception(exc)}") from exc

    async def _bootstrap_workspace(self, session: WorkspaceKernelSession) -> None:
        await WorkspaceOfflineAdapter().ensure_database_file(session.workspace_duckdb_path)
        duckdb_path = Path(session.workspace_duckdb_path).as_posix()
        bootstrap_code = (
            "import duckdb\n"
            "import json as _json\n"
            "import uuid as _uuid\n"
            "from pathlib import Path as _Path\n"
            "from datetime import datetime as _dt, timedelta as _td, timezone as _tz\n"
            "try:\n"
            "    import pandas as _pd_display\n"
            "    _pd_display.set_option('display.max_rows', 1000)\n"
            "    _pd_display.set_option('display.min_rows', 20)\n"
            "    _pd_display.set_option('display.max_columns', 20)\n"
            "    _pd_display.set_option('display.large_repr', 'truncate')\n"
            "except Exception:\n"
            "    pass\n"
            f"conn = duckdb.connect(r'''{duckdb_path}''', read_only=True)\n"
            "if \"_inquira_run_exports\" not in globals():\n"
            "    _inquira_run_exports = {}\n"
            "if \"_inquira_active_run_id\" not in globals():\n"
            "    _inquira_active_run_id = None\n"
            "if \"_inquira_active_turn_context\" not in globals():\n"
            "    _inquira_active_turn_context = {}\n"
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
            "def set_active_run(run_id, conversation_id=None, turn_id=None, artifact_dir=None):\n"
            "    global _inquira_active_run_id, _inquira_active_turn_context\n"
            "    _inquira_active_run_id = str(run_id)\n"
            "    _inquira_active_turn_context[_inquira_active_run_id] = {\n"
            "        'conversation_id': str(conversation_id or ''),\n"
            "        'turn_id': str(turn_id or ''),\n"
            "        'artifact_dir': str(artifact_dir or ''),\n"
            "    }\n"
            "    if _inquira_active_run_id not in _inquira_run_exports:\n"
            "        _inquira_run_exports[_inquira_active_run_id] = []\n"
            "    return _inquira_active_run_id\n"
            "def _inquira_get_active_exports(run_id=None):\n"
            "    key = str(run_id or _inquira_active_run_id or '')\n"
            "    return list(_inquira_run_exports.get(key, []))\n"
            "def _inquira_artifact_path(run_id, artifact_id, kind):\n"
            "    context = _inquira_active_turn_context.get(str(run_id), {})\n"
            "    artifact_dir = str(context.get('artifact_dir') or '')\n"
            "    if not artifact_dir:\n"
            "        raise ValueError('No artifact_dir set. Call set_active_run(run_id, artifact_dir=...) first.')\n"
            "    extension = {'dataframe': 'parquet', 'figure': 'json', 'scalar': 'json', 'structured': 'json', 'text': 'txt'}.get(str(kind), 'json')\n"
            "    target = _Path(artifact_dir).expanduser()\n"
            "    target.mkdir(parents=True, exist_ok=True)\n"
            "    return target / (str(artifact_id) + '.' + extension)\n"
            "def _inquira_named_artifact_id(logical_name, kind):\n"
            "    return _inquira_safe_name(logical_name or kind or 'artifact') + '__' + str(_uuid.uuid4())\n"
            "def _inquira_replace_run_export(run_id, kind, logical_name, envelope):\n"
            "    existing = []\n"
            "    for item in _inquira_run_exports.get(str(run_id), []):\n"
            "        if str(item.get('kind')) == str(kind) and str(item.get('logical_name')) == str(logical_name):\n"
            "            old_path = str(item.get('storage_path') or '')\n"
            "            if old_path:\n"
            "                try:\n"
            "                    _Path(old_path).unlink(missing_ok=True)\n"
            "                except Exception:\n"
            "                    pass\n"
            "            continue\n"
            "        existing.append(item)\n"
            "    existing.append(envelope)\n"
            "    _inquira_run_exports[str(run_id)] = existing\n"
            "def _inquira_export_envelope(*, artifact_id, run_id, kind, logical_name, storage_path=None, table_name=None, row_count=None, schema=None, preview_rows=None, payload=None, status='ready', error=None):\n"
            "    now, expires = _inquira_now_and_expiry()\n"
            "    context = _inquira_active_turn_context.get(str(run_id), {})\n"
            "    return {\n"
            "      'artifact_id': str(artifact_id),\n"
            "      'run_id': str(run_id),\n"
            "      'kind': str(kind),\n"
            "      'pointer': str(storage_path or ''),\n"
            "      'storage_path': str(storage_path or ''),\n"
            "      'conversation_id': str(context.get('conversation_id') or ''),\n"
            "      'turn_id': str(context.get('turn_id') or ''),\n"
            "      'logical_name': str(logical_name),\n"
            "      'row_count': int(row_count) if row_count is not None else None,\n"
            "      'schema': schema,\n"
            "      'preview_rows': preview_rows or [],\n"
            "      'payload': payload,\n"
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
            "    try:\n"
            "        import pyarrow as _pa\n"
            "    except Exception:\n"
            "        _pa = None\n"
            "    if _pl is not None and isinstance(df, _pl.LazyFrame):\n"
            "        df = df.collect()\n"
            "    if _pl is not None and isinstance(df, _pl.DataFrame):\n"
            "        pdf = df.to_pandas()\n"
            "    elif _pa is not None and isinstance(df, _pa.Table):\n"
            "        pdf = df.to_pandas()\n"
            "    elif _pa is not None and isinstance(df, _pa.RecordBatch):\n"
            "        pdf = _pa.Table.from_batches([df]).to_pandas()\n"
            "    elif _pa is not None and hasattr(_pa, 'RecordBatchReader') and isinstance(df, _pa.RecordBatchReader):\n"
            "        pdf = df.read_all().to_pandas()\n"
            "    elif isinstance(df, _pd.DataFrame):\n"
            "        pdf = df\n"
            "    else:\n"
            "        pdf = _pd.DataFrame(df)\n"
            "    artifact_id = _inquira_named_artifact_id(logical_name, 'dataframe')\n"
            "    storage_path = _inquira_artifact_path(active_run, artifact_id, 'dataframe')\n"
            "    _export_con = duckdb.connect(':memory:')\n"
            "    try:\n"
            "        _export_con.register('_inquira_df_tmp', pdf)\n"
            "        _safe_storage_path = str(storage_path).replace(\"'\", \"''\")\n"
            "        _export_con.execute(f\"COPY (SELECT * FROM _inquira_df_tmp) TO '{_safe_storage_path}' (FORMAT PARQUET)\")\n"
            "    finally:\n"
            "        try:\n"
            "            _export_con.unregister('_inquira_df_tmp')\n"
            "        except Exception:\n"
            "            pass\n"
            "        _export_con.close()\n"
            "    row_count = int(len(pdf.index))\n"
            "    schema = [{'name': str(col), 'dtype': str(dtype)} for col, dtype in pdf.dtypes.items()]\n"
            "    preview_rows = _json.loads(pdf.head(20).to_json(orient='records', date_format='iso'))\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='dataframe', logical_name=str(logical_name), storage_path=str(storage_path), row_count=row_count, schema=schema, preview_rows=preview_rows, payload={'title': title, 'insight': insight})\n"
            "    _inquira_replace_run_export(active_run, 'dataframe', str(logical_name), envelope)\n"
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
            "    artifact_id = _inquira_named_artifact_id(logical_name, 'figure')\n"
            "    storage_path = _inquira_artifact_path(active_run, artifact_id, 'figure')\n"
            "    payload = {'figure': fig_payload, 'title': title, 'insight': insight}\n"
            "    storage_path.write_text(_json.dumps(payload, default=str), encoding='utf-8')\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='figure', logical_name=str(logical_name), storage_path=str(storage_path), preview_rows=[], payload=payload)\n"
            "    _inquira_replace_run_export(active_run, 'figure', str(logical_name), envelope)\n"
            "    return envelope\n"
            "def export_scalar(value, logical_name, run_id=None, meta=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No active run_id set. Call set_active_run(run_id) first.')\n"
            "    artifact_id = _inquira_named_artifact_id(logical_name, 'scalar')\n"
            "    storage_path = _inquira_artifact_path(active_run, artifact_id, 'scalar')\n"
            "    payload = {'value': value, 'meta': meta}\n"
            "    storage_path.write_text(_json.dumps(payload, default=str), encoding='utf-8')\n"
            "    envelope = _inquira_export_envelope(artifact_id=artifact_id, run_id=active_run, kind='scalar', logical_name=str(logical_name), storage_path=str(storage_path), preview_rows=[], payload=payload)\n"
            "    _inquira_replace_run_export(active_run, 'scalar', str(logical_name), envelope)\n"
            "    return envelope\n"
            "def finalize_run(run_id, metadata=None):\n"
            "    active_run = str(run_id or _inquira_active_run_id or '')\n"
            "    if not active_run:\n"
            "        raise ValueError('No run_id provided to finalize_run')\n"
            "    payload = metadata or {}\n"
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
        identifier_ref = self._extract_identifier_reference(code)

        should_probe_fallback = (
            parsed.error is None
            and (
                parsed.result is None
                or parsed.result_type in {None, "scalar"}
            )
        )

        if should_probe_fallback:
            preferred_probe_applied = False
            if identifier_ref:
                preferred_probe = await self._execute_request(
                    session,
                    _build_identifier_result_probe_code(identifier_ref),
                )
                if (
                    preferred_probe.result is not None
                    and preferred_probe.result_type in {"DataFrame", "Figure"}
                ):
                    parsed.result = preferred_probe.result
                    parsed.result_type = preferred_probe.result_type
                    preferred_probe_applied = True
                elif (
                    parsed.result is None
                    and preferred_probe.result is not None
                    and preferred_probe.result_type is not None
                ):
                    parsed.result = preferred_probe.result
                    parsed.result_type = preferred_probe.result_type
                    preferred_probe_applied = True

            if not preferred_probe_applied:
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
        *,
        iopub_idle_timeout: float = 90.0,
    ) -> ParsedExecutionOutput:
        msg_id = session.client.execute(code, store_history=True, stop_on_error=True)
        parsed = ParsedExecutionOutput()
        deadline = time.monotonic() + max(1.0, float(iopub_idle_timeout))

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for kernel IOPub idle status.")
            try:
                msg = await session.client.get_iopub_msg(timeout=min(1, remaining))
            except (QueueEmpty, asyncio.TimeoutError):
                continue
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
        try:
            await self._await_maybe(session.manager.shutdown_kernel(now=True))
        finally:
            await self._release_runtime_lease(session)

    async def _acquire_runtime_lease(self, session: WorkspaceKernelSession) -> None:
        owner_token = str(session.runtime_lease_owner_token or "").strip()
        if not owner_token:
            return
        async with AppDataSessionLocal() as db:
            try:
                lease = await self._lease_coordinator.acquire_workspace_runtime_lease(
                    db,
                    workspace_id=session.workspace_id,
                    owner_token=owner_token,
                    metadata={"source": "workspace_kernel_manager"},
                )
            except LeaseConflictError as exc:
                await db.rollback()
                raise RuntimeError(
                    "Workspace runtime cannot start because maintenance mode is active for this workspace."
                ) from exc
            await db.commit()
        self._cache_runtime_lease(session, getattr(lease, "leased_until", None))

    async def _renew_runtime_lease(self, session: WorkspaceKernelSession) -> bool:
        owner_token = str(session.runtime_lease_owner_token or "").strip()
        if not owner_token:
            return False
        async with AppDataSessionLocal() as db:
            try:
                lease = await self._lease_coordinator.renew_lease(
                    db,
                    resource_key=session.workspace_id,
                    lease_kind=LeaseKinds.WORKSPACE_RUNTIME,
                    owner_token=owner_token,
                    metadata={"source": "workspace_kernel_manager"},
                )
            except LeaseConflictError:
                await db.rollback()
                return False
            await db.commit()
        self._cache_runtime_lease(session, getattr(lease, "leased_until", None))
        return True

    async def _release_runtime_lease(self, session: WorkspaceKernelSession) -> None:
        owner_token = str(session.runtime_lease_owner_token or "").strip()
        if not owner_token:
            return
        async with AppDataSessionLocal() as db:
            await self._lease_coordinator.release_lease(
                db,
                resource_key=session.workspace_id,
                lease_kind=LeaseKinds.WORKSPACE_RUNTIME,
                owner_token=owner_token,
            )
            await db.commit()
        session.runtime_lease_expires_at = None
        session.runtime_lease_renew_after = None

    async def _touch_session(self, session: WorkspaceKernelSession) -> None:
        now = datetime.now(UTC)
        session.last_used = now
        if not self._should_renew_runtime_lease(session, now):
            return
        try:
            await self._renew_runtime_lease(session)
        except Exception as exc:
            if self._cached_runtime_lease_still_valid(session, now):
                session.runtime_lease_renew_after = now + timedelta(seconds=10)
                logprint(
                    (
                        "Workspace runtime lease renewal deferred "
                        f"for workspace {session.workspace_id}: {exc}"
                    ),
                    level="warning",
                )
                return
            raise

    def _cache_runtime_lease(
        self,
        session: WorkspaceKernelSession,
        leased_until: datetime | None,
    ) -> None:
        if leased_until is None:
            session.runtime_lease_expires_at = None
            session.runtime_lease_renew_after = None
            return
        expires_at = ResourceLeaseCoordinator._normalize_dt(leased_until)
        session.runtime_lease_expires_at = expires_at
        session.runtime_lease_renew_after = expires_at - self._lease_renewal_margin()

    def _lease_renewal_margin(self) -> timedelta:
        margin_seconds = max(
            30,
            min(120, int(self._runtime_lease_delta.total_seconds() / 3)),
        )
        return timedelta(seconds=margin_seconds)

    @staticmethod
    def _should_renew_runtime_lease(
        session: WorkspaceKernelSession,
        now: datetime,
    ) -> bool:
        renew_after = session.runtime_lease_renew_after
        if renew_after is None:
            return True
        return ResourceLeaseCoordinator._normalize_dt(renew_after) <= now

    @staticmethod
    def _cached_runtime_lease_still_valid(
        session: WorkspaceKernelSession,
        now: datetime,
    ) -> bool:
        expires_at = session.runtime_lease_expires_at
        if expires_at is None:
            return False
        return ResourceLeaseCoordinator._normalize_dt(expires_at) > now

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
        if identifier_ref and kind in {"dataframe", "figure", "scalar"}:
            return kind, identifier_ref
        if kind in {"dataframe", "figure", "scalar"}:
            return kind, None
        if parsed.result is not None:
            return "scalar", None
        return "none", None
