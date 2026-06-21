"""Server-side Python execution for Inquira."""

from __future__ import annotations

import asyncio
from typing import Any

from app.services.execution_config import load_execution_runtime_config
from app.services.workspace_kernel_manager import WorkspaceKernelManager

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


async def get_workspace_runtime_status(workspace_id: str) -> str:
    """Return status for a workspace runtime."""
    return await get_workspace_kernel_status(workspace_id)


async def list_workspace_runtime_snapshots() -> list[dict[str, Any]]:
    """Return status snapshots for active workspace runtimes."""
    manager = await get_workspace_kernel_manager()
    return await manager.list_session_snapshots()


def _kernel_required_message(operation_name: str, status: str) -> str:
    operation = str(operation_name or "This operation").strip() or "This operation"
    if status == "error":
        return (
            f"{operation} requires an active workspace runtime. The current workspace runtime "
            "needs attention. Retry the workspace action and try again."
        )
    if status == "starting":
        return (
            f"{operation} requires the workspace runtime to finish starting. Wait for the "
            "workspace to be ready, then try again."
        )
    return (
        f"{operation} requires an active workspace runtime. Open the workspace and try again "
        "after it is ready."
    )


async def ensure_workspace_kernel_active(workspace_id: str, operation_name: str) -> None:
    """Raise a clear error when an operation requires a live workspace kernel."""
    status = await get_workspace_kernel_status(workspace_id)
    if status in {"ready", "busy"}:
        return
    raise RuntimeError(_kernel_required_message(operation_name, status))


async def interrupt_workspace_kernel(workspace_id: str) -> bool:
    """Interrupt a workspace kernel."""
    manager = await get_workspace_kernel_manager()
    return await manager.interrupt_workspace(workspace_id)


async def ingest_workspace_dataset_via_kernel(
    *,
    workspace_id: str,
    source_path: str,
    table_name: str,
    file_type: str,
) -> dict[str, Any]:
    """Import a dataset through the active workspace kernel."""
    await ensure_workspace_kernel_active(workspace_id, "Loading a dataset")
    manager = await get_workspace_kernel_manager()
    result = await manager.ingest_dataset(
        workspace_id=workspace_id,
        source_path=source_path,
        table_name=table_name,
        file_type=file_type,
    )
    if result is None:
        raise RuntimeError(_kernel_required_message("Loading a dataset", "missing"))
    return result


async def get_workspace_columns_via_kernel(
    workspace_id: str,
) -> list[dict[str, str]]:
    """Read workspace column catalog through the active kernel-owned connection."""
    await ensure_workspace_kernel_active(workspace_id, "Loading workspace columns")
    manager = await get_workspace_kernel_manager()
    return await manager.get_workspace_columns(workspace_id=workspace_id)


async def get_workspace_table_schema_via_kernel(
    *,
    workspace_id: str,
    table_name: str,
    allow_sample_values: bool = False,
) -> list[dict[str, Any]] | None:
    """Describe one workspace table through the active kernel-owned connection."""
    await ensure_workspace_kernel_active(workspace_id, "Loading dataset schema")
    manager = await get_workspace_kernel_manager()
    return await manager.get_workspace_table_schema(
        workspace_id=workspace_id,
        table_name=table_name,
        allow_sample_values=allow_sample_values,
    )


async def execute_code(
    code: str,
    timeout: int = 60,
    working_dir: str | None = None,
    workspace_id: str | None = None,
    workspace_duckdb_path: str | None = None,
) -> dict[str, Any]:
    """Execute code using the workspace-scoped Jupyter runtime."""
    if not code or not code.strip():
        return _error_payload("No code provided")

    config = load_execution_runtime_config()
    provider = config.provider.strip().lower()

    if provider != "local_jupyter":
        return _error_payload(
            f"Unsupported execution provider '{config.provider}'. "
            "Only 'local_jupyter' is supported."
        )

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


async def bootstrap_workspace_runtime(
    *,
    workspace_id: str,
    workspace_duckdb_path: str,
    progress_callback: Any | None = None,
) -> bool:
    """Ensure workspace runtime environment + kernel are ready."""
    config = load_execution_runtime_config()
    provider = config.provider.strip().lower()
    if provider != "local_jupyter":
        return False
    manager = await get_workspace_kernel_manager()
    return await manager.ensure_ready(
        workspace_id=workspace_id,
        workspace_duckdb_path=workspace_duckdb_path,
        config=config,
        progress_callback=progress_callback,
    )


def _error_payload(message: str) -> dict[str, Any]:
    """Return a standardized execution error payload."""
    return {
        "success": False,
        "stdout": "",
        "stderr": message,
        "has_stdout": False,
        "has_stderr": True,
        "error": message,
        "result": None,
        "result_type": None,
        "result_kind": "error",
        "result_name": None,
        "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
    }
