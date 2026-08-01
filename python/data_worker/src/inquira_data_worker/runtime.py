"""Persistent worker RPC methods for workspace analysis kernels."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .langgraph_agent import LangGraphAnalysisAgent
from .artifacts import inspect_parquet, query_parquet
from .commands import CommandExecutionError, compile_command
from .errors import AdapterError
from .kernel import WorkspaceKernelManager
from .rpc import handle_request as handle_data_request
from .schema_generation import SchemaGenerator


@dataclass(frozen=True)
class ActiveAgentTask:
    client_request_id: str
    task: asyncio.Task[Any]


class WorkerRuntime:
    def __init__(self) -> None:
        self.kernels = WorkspaceKernelManager()
        self.agent = LangGraphAnalysisAgent(kernels=self.kernels)
        self.schema_generator = SchemaGenerator()
        self._agent_tasks: dict[str, ActiveAgentTask] = {}

    async def handle(
        self, request: dict[str, Any], emit: Callable[[dict[str, Any]], Any]
    ) -> dict[str, Any]:
        request_id = request.get("id") if isinstance(request, dict) else None
        response = {"id": request_id, "result": None, "error": None}
        try:
            if (
                not isinstance(request, dict)
                or not request_id
                or not isinstance(request.get("method"), str)
            ):
                raise RuntimeRequestError(
                    "invalid_request", "RPC request requires an id and method."
                )
            params = request.get("params")
            if not isinstance(params, dict):
                raise RuntimeRequestError(
                    "invalid_params", "RPC params must be an object."
                )
            method = request["method"]
            if method in {"discover", "preview", "materialize", "build_catalog", "preview_catalog"}:
                return await asyncio.to_thread(handle_data_request, request)
            if method == "ping":
                response["result"] = {"status": "ready"}
            elif method == "kernel_execute":
                values = _execution_params(params)

                async def forward(event: dict[str, Any]) -> None:
                    emitted = emit(event)
                    if hasattr(emitted, "__await__"):
                        await emitted

                response["result"] = await self.kernels.execute(**values, emit=forward)
            elif method == "agent_analyze":

                workspace_id = _workspace_id(params)
                client_request_id = _client_request_id(params, fallback=str(request_id))
                current_task = asyncio.current_task()
                active = self._agent_tasks.get(workspace_id)
                if active is not None and not active.task.done():
                    raise RuntimeRequestError(
                        "agent_busy", "An analysis is already running for this workspace."
                    )
                if current_task is None:
                    raise RuntimeRequestError(
                        "worker_internal_error", "The agent task could not be registered."
                    )
                self._agent_tasks[workspace_id] = ActiveAgentTask(client_request_id, current_task)

                async def forward_agent(event: dict[str, Any]) -> None:
                    emitted = emit(event)
                    if hasattr(emitted, "__await__"):
                        await emitted

                try:
                    response["result"] = await self.agent.analyze(params, forward_agent)
                finally:
                    current = self._agent_tasks.get(workspace_id)
                    if current is not None and current.task is current_task:
                        self._agent_tasks.pop(workspace_id, None)
            elif method == "agent_cancel":
                workspace_id = _workspace_id(params)
                client_request_id = _client_request_id(params)
                active = self._agent_tasks.get(workspace_id)
                cancelled = (
                    active is not None
                    and active.client_request_id == client_request_id
                    and not active.task.done()
                )
                if cancelled:
                    active.task.cancel()
                    await self.kernels.interrupt(workspace_id)
                response["result"] = {
                    "workspace_id": workspace_id,
                    "client_request_id": client_request_id,
                    "cancelled": cancelled,
                }
            elif method == "schema_describe":
                response["result"] = await self.schema_generator.generate(params)
            elif method == "command_compile":
                response["result"] = compile_command(params)
            elif method == "artifact_inspect":
                response["result"] = await asyncio.to_thread(
                    inspect_parquet, _artifact_path(params)
                )
            elif method == "artifact_rows":
                path = _artifact_path(params)
                offset = params.get("offset", 0)
                limit = params.get("limit", 1000)
                sort_model = params.get("sort_model", [])
                filter_model = params.get("filter_model", {})
                search_text = params.get("search_text", "")
                if (
                    not isinstance(sort_model, list)
                    or not isinstance(filter_model, dict)
                    or not isinstance(search_text, str)
                ):
                    raise RuntimeRequestError(
                        "invalid_params", "Artifact query models are invalid."
                    )
                response["result"] = await asyncio.to_thread(
                    query_parquet,
                    path,
                    offset=offset,
                    limit=limit,
                    sort_model=sort_model,
                    filter_model=filter_model,
                    search_text=search_text,
                )
            elif method == "kernel_status":
                workspace_id = _workspace_id(params)
                response["result"] = {
                    "workspace_id": workspace_id,
                    "status": await self.kernels.status(workspace_id),
                }
            elif method == "kernel_reset":
                workspace_id = _workspace_id(params)
                response["result"] = {
                    "workspace_id": workspace_id,
                    "reset": await self.kernels.reset(workspace_id),
                }
            elif method == "kernel_interrupt":
                workspace_id = _workspace_id(params)
                response["result"] = {
                    "workspace_id": workspace_id,
                    "interrupted": await self.kernels.interrupt(workspace_id),
                }
            else:
                raise RuntimeRequestError(
                    "method_not_found", f"RPC method {method} was not found."
                )
        except asyncio.CancelledError:
            response["error"] = {
                "code": "agent_cancelled",
                "message": "The analysis was cancelled.",
            }
        except RuntimeRequestError as exc:
            response["error"] = {"code": exc.code, "message": exc.message}
        except AdapterError as exc:
            response["error"] = {"code": exc.code, "message": exc.message}
        except CommandExecutionError as exc:
            response["error"] = {"code": "command_invalid", "message": str(exc)}
        except Exception as exc:
            response["error"] = {
                "code": "worker_internal_error",
                "message": str(exc) or "The worker could not complete the request.",
            }
        return response

    async def shutdown(self) -> None:
        tasks = [active.task for active in self._agent_tasks.values() if not active.task.done()]
        self._agent_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.kernels.shutdown()


class RuntimeRequestError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _workspace_id(params: dict[str, Any]) -> str:
    value = params.get("workspace_id")
    if (
        not isinstance(value, str)
        or not value.strip()
        or Path(value).name != value
        or "/" in value
        or "\\" in value
    ):
        raise RuntimeRequestError("invalid_params", "workspace_id is invalid.")
    return value


def _client_request_id(params: dict[str, Any], *, fallback: str = "") -> str:
    value = params.get("client_request_id", fallback)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 128:
        raise RuntimeRequestError("invalid_params", "client_request_id is invalid.")
    return value.strip()


def _artifact_path(params: dict[str, Any]) -> str:
    value = params.get("artifact_path")
    if not isinstance(value, str):
        raise RuntimeRequestError("invalid_params", "artifact_path is required.")
    return value


def _execution_params(params: dict[str, Any]) -> dict[str, Any]:
    workspace_id = _workspace_id(params)
    database_path = params.get("database_path")
    code = params.get("code")
    run_id = params.get("run_id")
    artifact_dir = params.get("artifact_dir")
    timeout = params.get("timeout_seconds")
    if (
        not isinstance(database_path, str)
        or not Path(database_path).expanduser().is_file()
    ):
        raise RuntimeRequestError(
            "invalid_params",
            "database_path must identify an existing workspace catalog.",
        )
    if not isinstance(code, str) or not code.strip():
        raise RuntimeRequestError("invalid_params", "code is required.")
    if not isinstance(run_id, str) or not run_id.strip() or Path(run_id).name != run_id:
        raise RuntimeRequestError("invalid_params", "run_id is invalid.")
    if (
        not isinstance(artifact_dir, str)
        or not Path(artifact_dir).expanduser().is_absolute()
    ):
        raise RuntimeRequestError("invalid_params", "artifact_dir must be absolute.")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 3600:
        raise RuntimeRequestError(
            "invalid_params", "timeout_seconds must be between 1 and 3600."
        )
    return {
        "workspace_id": workspace_id,
        "database_path": str(Path(database_path).expanduser().resolve()),
        "code": code,
        "run_id": run_id,
        "artifact_dir": str(Path(artifact_dir).expanduser().resolve()),
        "timeout_seconds": timeout,
    }
