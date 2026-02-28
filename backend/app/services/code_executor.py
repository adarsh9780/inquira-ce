"""Server-side Python execution providers for Inquira."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from app.core.logger import logprint
from app.services.execution_config import load_execution_runtime_config
from app.services.workspace_kernel_manager import WorkspaceKernelManager

_SUBPROCESS_WRAPPER_TEMPLATE = """
import builtins as _bi
import io
import json
import sys
import traceback

_captured_stdout = io.StringIO()
_captured_stderr = io.StringIO()
_old_stdout = sys.stdout
_old_stderr = sys.stderr
sys.stdout = _captured_stdout
sys.stderr = _captured_stderr
_result = None

try:
{indented_code}
    _last_val = _bi.__dict__.get("_")
    if _last_val is not None:
        _result = _last_val
except Exception:
    traceback.print_exc(file=_captured_stderr)

sys.stdout = _old_stdout
sys.stderr = _old_stderr

def _serialize(obj):
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return {{"type": "DataFrame", "data": json.loads(obj.to_json(orient="split", date_format="iso"))}}
    except Exception:
        pass
    try:
        import plotly.graph_objects as go
        if isinstance(obj, go.Figure):
            return {{"type": "Figure", "data": json.loads(obj.to_json())}}
    except Exception:
        pass
    if obj is not None:
        try:
            json.dumps(obj)
            return {{"type": "scalar", "data": obj}}
        except Exception:
            return {{"type": "scalar", "data": repr(obj)}}
    return None

print("__INQUIRA_RESULT__" + json.dumps({{
    "stdout": _captured_stdout.getvalue(),
    "stderr": _captured_stderr.getvalue(),
    "result": _serialize(_result),
}}))
"""

_workspace_kernel_manager: WorkspaceKernelManager | None = None
_workspace_kernel_manager_lock = asyncio.Lock()


async def get_workspace_kernel_manager() -> WorkspaceKernelManager:
    """Return singleton kernel manager configured from runtime settings."""
    global _workspace_kernel_manager
    if _workspace_kernel_manager is not None:
        return _workspace_kernel_manager

    async with _workspace_kernel_manager_lock:
        if _workspace_kernel_manager is None:
            config = load_execution_runtime_config()
            _workspace_kernel_manager = WorkspaceKernelManager(
                idle_minutes=config.kernel_idle_minutes
            )
    return _workspace_kernel_manager


async def shutdown_workspace_kernel_manager() -> None:
    """Shutdown singleton kernel manager and dispose active kernels."""
    global _workspace_kernel_manager
    async with _workspace_kernel_manager_lock:
        manager = _workspace_kernel_manager
        _workspace_kernel_manager = None
    if manager is not None:
        await manager.shutdown()


async def prune_idle_workspace_kernels() -> None:
    """Shutdown kernels that exceeded configured idle threshold."""
    manager = await get_workspace_kernel_manager()
    await manager.prune_idle_sessions()


async def reset_workspace_kernel(workspace_id: str) -> bool:
    """Reset a workspace kernel and clear persisted Python context."""
    manager = await get_workspace_kernel_manager()
    return await manager.reset_workspace(workspace_id)


async def get_workspace_kernel_status(workspace_id: str) -> str:
    """Return status for workspace kernel."""
    manager = await get_workspace_kernel_manager()
    return await manager.get_status(workspace_id)


async def interrupt_workspace_kernel(workspace_id: str) -> bool:
    """Interrupt a workspace kernel."""
    manager = await get_workspace_kernel_manager()
    return await manager.interrupt_workspace(workspace_id)


async def get_workspace_dataframe_rows(
    workspace_id: str,
    artifact_id: str,
    offset: int = 0,
    limit: int = 1000,
) -> dict[str, Any] | None:
    """Fetch a paginated slice of a stored dataframe artifact."""
    manager = await get_workspace_kernel_manager()
    return await manager.get_dataframe_rows(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        offset=offset,
        limit=limit,
    )


async def execute_code(
    code: str,
    timeout: int = 60,
    working_dir: str | None = None,
    workspace_id: str | None = None,
    workspace_duckdb_path: str | None = None,
) -> dict[str, Any]:
    """Execute code using configured provider while preserving legacy response schema."""
    if not code or not code.strip():
        return _error_payload("No code provided")

    config = load_execution_runtime_config()
    provider = config.provider.strip().lower()

    if provider == "local_jupyter":
        if not workspace_id:
            return _error_payload(
                "Execution provider 'local_jupyter' requires workspace_id."
            )
        if not workspace_duckdb_path:
            return _error_payload(
                "Execution provider 'local_jupyter' requires workspace_duckdb_path."
            )
        manager = await get_workspace_kernel_manager()
        return await manager.execute(
            workspace_id=workspace_id,
            workspace_duckdb_path=workspace_duckdb_path,
            code=code,
            timeout=timeout,
            config=config,
        )

    if provider == "local_subprocess":
        return await _execute_with_subprocess(
            code=code,
            timeout=timeout,
            working_dir=working_dir,
        )

    return _error_payload(
        f"Unsupported execution provider '{config.provider}'. "
        "Supported values: local_jupyter, local_subprocess."
    )


def _error_payload(message: str) -> dict[str, Any]:
    """Return a standardized execution error payload."""
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "error": message,
        "result": None,
        "result_type": None,
        "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
    }


async def _execute_with_subprocess(
    *,
    code: str,
    timeout: int,
    working_dir: str | None,
) -> dict[str, Any]:
    indented = "\n".join(f"    {line}" for line in code.splitlines())
    wrapper = _SUBPROCESS_WRAPPER_TEMPLATE.format(indented_code=indented)
    if working_dir is None:
        working_dir = os.path.expanduser("~/.inquira/runtime/exec_tmp")
    Path(working_dir).mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        dir=working_dir,
        encoding="utf-8",
    ) as handle:
        handle.write(wrapper)
        handle.flush()
        script_path = handle.name

    try:
        return await asyncio.to_thread(
            _run_in_subprocess,
            script_path=script_path,
            timeout=timeout,
            working_dir=working_dir,
        )
    except subprocess.TimeoutExpired:
        return _error_payload(f"Execution timed out after {timeout} seconds.")
    except Exception as exc:
        logprint(f"Code execution error: {exc}", level="error")
        return _error_payload(str(exc))
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def _run_in_subprocess(script_path: str, timeout: int, working_dir: str) -> dict[str, Any]:
    """Execute wrapper script in local interpreter and parse output payload."""
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=working_dir,
        stdin=subprocess.PIPE,
    )
    return _parse_subprocess_output(result.stdout, result.stderr, result.returncode)


def _parse_subprocess_output(
    stdout_raw: str,
    stderr_raw: str,
    returncode: int,
) -> dict[str, Any]:
    """Parse subprocess output marker into legacy frontend payload."""
    parsed_result: Any | None = None
    result_type: str | None = None
    clean_stdout = stdout_raw

    if "__INQUIRA_RESULT__" in stdout_raw:
        parts = stdout_raw.split("__INQUIRA_RESULT__", 1)
        clean_stdout = parts[0]
        try:
            payload = json.loads(parts[1].strip())
            clean_stdout = str(payload.get("stdout", clean_stdout))
            stderr_raw = str(payload.get("stderr", stderr_raw) or stderr_raw)
            result_block = payload.get("result")
            if isinstance(result_block, dict):
                result_type = (
                    str(result_block.get("type"))
                    if result_block.get("type") is not None
                    else None
                )
                parsed_result = result_block.get("data")
        except (json.JSONDecodeError, IndexError, TypeError, ValueError):
            pass

    stderr = stderr_raw.strip()
    success = returncode == 0 and not stderr
    return {
        "success": success,
        "stdout": clean_stdout.strip(),
        "stderr": stderr,
        "error": stderr if not success else None,
        "result": parsed_result,
        "result_type": result_type,
    }
