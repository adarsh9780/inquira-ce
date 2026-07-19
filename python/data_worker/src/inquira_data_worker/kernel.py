"""Workspace-scoped persistent Jupyter kernel lifecycle."""

from __future__ import annotations

import ast
import asyncio
import inspect
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty as QueueEmpty
from typing import Any, Callable

from jupyter_client import AsyncKernelManager

from .jupyter_messages import ExecutionOutput


@dataclass
class KernelSession:
    workspace_id: str
    database_path: str
    manager: AsyncKernelManager
    client: Any
    status: str = "ready"
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_used: float = field(default_factory=time.monotonic)


class WorkspaceKernelManager:
    def __init__(self, *, idle_seconds: int = 1800) -> None:
        self._sessions: dict[str, KernelSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._idle_seconds = max(1, int(idle_seconds))

    @property
    def session_count(self) -> int:
        return len(self._sessions)

    async def execute(
        self,
        *,
        workspace_id: str,
        database_path: str,
        code: str,
        run_id: str,
        artifact_dir: str,
        timeout_seconds: int,
        emit: Callable[[dict[str, Any]], Any] | None = None,
    ) -> dict[str, Any]:
        session = await self._get_or_start(workspace_id, database_path, emit)
        async with session.lock:
            session.status = "busy"
            await _emit(emit, {"type": "kernel_status", "status": "busy", "workspace_id": workspace_id})
            session.last_used = time.monotonic()
            try:
                await self._execute_request(
                    session,
                    f"set_active_run({run_id!r}, {str(Path(artifact_dir).resolve())!r})",
                )
                primary = await asyncio.wait_for(
                    self._execute_request(session, code, emit=emit),
                    timeout=max(1, int(timeout_seconds)),
                )
                artifacts: list[dict[str, Any]] = []
                if primary.error is None:
                    candidate = _capture_candidate(code)
                    if candidate is not None:
                        expression, logical_name = candidate
                        captured = await self._execute_request(
                            session,
                            f"_inquira_emit_capture({expression}, logical_name={logical_name!r})",
                        )
                        if captured.result_kind in {"dataframe", "figure", "scalar", "text"}:
                            primary.result = captured.result
                            primary.result_kind = captured.result_kind
                    exports = await self._execute_request(session, f"_inquira_emit_exports({run_id!r})")
                    if exports.result_kind == "exports" and isinstance(exports.result, list):
                        artifacts = [item for item in exports.result if isinstance(item, dict)]
                response = primary.response()
                response["artifacts"] = artifacts
                response["timed_out"] = False
                return response
            except asyncio.TimeoutError:
                await self._interrupt_session(session)
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": f"Execution timed out after {timeout_seconds} seconds.",
                    "result": None,
                    "result_kind": "error",
                    "artifacts": [],
                    "timed_out": True,
                }
            finally:
                session.status = "ready"
                session.last_used = time.monotonic()
                await _emit(emit, {"type": "kernel_status", "status": "ready", "workspace_id": workspace_id})

    async def status(self, workspace_id: str) -> str:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        return session.status if session is not None else "missing"

    async def reset(self, workspace_id: str) -> bool:
        async with self._sessions_lock:
            session = self._sessions.pop(workspace_id, None)
        if session is None:
            return False
        await self._shutdown_session(session)
        return True

    async def interrupt(self, workspace_id: str) -> bool:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
        if session is None:
            return False
        await self._interrupt_session(session)
        return True

    async def prune_idle(self) -> int:
        cutoff = time.monotonic() - self._idle_seconds
        async with self._sessions_lock:
            stale_ids = [
                workspace_id for workspace_id, session in self._sessions.items()
                if session.last_used < cutoff and not session.lock.locked()
            ]
            sessions = [self._sessions.pop(workspace_id) for workspace_id in stale_ids]
        for session in sessions:
            await self._shutdown_session(session)
        return len(sessions)

    async def shutdown(self) -> None:
        async with self._sessions_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await self._shutdown_session(session)

    async def _get_or_start(
        self,
        workspace_id: str,
        database_path: str,
        emit: Callable[[dict[str, Any]], Any] | None,
    ) -> KernelSession:
        async with self._sessions_lock:
            session = self._sessions.get(workspace_id)
            if session is not None and session.database_path == database_path:
                return session
            if session is not None:
                await self._shutdown_session(session)
            session = await self._start(workspace_id, database_path, emit)
            self._sessions[workspace_id] = session
            return session

    async def _start(
        self,
        workspace_id: str,
        database_path: str,
        emit: Callable[[dict[str, Any]], Any] | None,
    ) -> KernelSession:
        database = Path(database_path).expanduser().resolve()
        if not database.is_file():
            raise RuntimeError("Workspace catalog is unavailable.")
        await _emit(emit, {"type": "kernel_status", "status": "starting", "workspace_id": workspace_id})
        manager = AsyncKernelManager(kernel_name="python3")
        kernel_spec = manager.kernel_spec
        if kernel_spec is None:
            raise RuntimeError("Python Jupyter kernelspec is unavailable.")
        kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        client = None
        try:
            await manager.start_kernel()
            client = manager.client()
            client.start_channels()
            await client.wait_for_ready(timeout=20)
            session = KernelSession(workspace_id, str(database), manager, client)
            await self._bootstrap(session)
            await _emit(emit, {"type": "kernel_status", "status": "ready", "workspace_id": workspace_id})
            return session
        except Exception:
            if client is not None:
                client.stop_channels()
            try:
                await manager.shutdown_kernel(now=True)
            except Exception:
                pass
            raise

    async def _execute_request(
        self,
        session: KernelSession,
        code: str,
        *,
        emit: Callable[[dict[str, Any]], Any] | None = None,
        idle_timeout: float = 90,
    ) -> ExecutionOutput:
        message_id = session.client.execute(code, store_history=True, stop_on_error=True)
        output = ExecutionOutput()
        deadline = time.monotonic() + max(1, idle_timeout)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for Jupyter output.")
            try:
                message = await session.client.get_iopub_msg(timeout=min(1, remaining))
            except (QueueEmpty, asyncio.TimeoutError):
                continue
            if message.get("parent_header", {}).get("msg_id") != message_id:
                continue
            message_type = str(message.get("msg_type") or "")
            content = message.get("content")
            if message_type == "status" and isinstance(content, dict) and content.get("execution_state") == "idle":
                break
            if isinstance(content, dict):
                forwarded: list[dict[str, Any]] = []
                output.update(message_type, content, forwarded.append)
                for event in forwarded:
                    await _emit(emit, event)
        return output

    async def _interrupt_session(self, session: KernelSession) -> None:
        await _await_maybe(session.manager.interrupt_kernel())
        try:
            await session.client.wait_for_ready(timeout=5)
        except Exception:
            await _await_maybe(session.manager.restart_kernel(now=True))
            await session.client.wait_for_ready(timeout=15)
            await self._bootstrap(session)

    async def _bootstrap(self, session: KernelSession) -> None:
        bootstrap = (
            "from inquira_data_worker.kernel_support import install as _inquira_install\n"
            f"_inquira_install(globals(), workspace_id={session.workspace_id!r}, database_path={session.database_path!r})"
        )
        output = await self._execute_request(session, bootstrap)
        if output.error is not None:
            raise RuntimeError(output.error)

    async def _shutdown_session(self, session: KernelSession) -> None:
        try:
            session.client.stop_channels()
        except Exception:
            pass
        try:
            await _await_maybe(session.manager.shutdown_kernel(now=True))
        except Exception:
            pass


def _capture_candidate(code: str) -> tuple[str, str] | None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    if not tree.body:
        return None
    final = tree.body[-1]
    if isinstance(final, ast.Expr):
        if isinstance(final.value, ast.Name):
            return final.value.id, final.value.id
        return "_", "result"
    if isinstance(final, (ast.Assign, ast.AnnAssign)):
        targets = final.targets if isinstance(final, ast.Assign) else [final.target]
        for target in reversed(targets):
            if isinstance(target, ast.Name):
                return target.id, target.id
    return None


async def _emit(callback: Callable[[dict[str, Any]], Any] | None, event: dict[str, Any]) -> None:
    if callback is None:
        return
    value = callback(event)
    if inspect.isawaitable(value):
        await value


async def _await_maybe(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
