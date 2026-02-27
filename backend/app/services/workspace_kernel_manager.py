"""Workspace-scoped Jupyter kernel lifecycle and execution orchestration."""

from __future__ import annotations

import asyncio
import inspect
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
            status="ready",
        )
        await self._bootstrap_workspace(session)
        return session

    async def _bootstrap_workspace(self, session: WorkspaceKernelSession) -> None:
        duckdb_path = Path(session.workspace_duckdb_path).as_posix()
        bootstrap_code = (
            "import duckdb\n"
            f"conn = duckdb.connect(r'''{duckdb_path}''', read_only=True)\n"
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

        return parsed.as_response()

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
