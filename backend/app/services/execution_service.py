"""Abstractions for workspace-scoped code execution."""

from __future__ import annotations

from typing import Any, Protocol, TypedDict

from .code_executor import execute_code, get_workspace_kernel_status


class ExecutionResult(TypedDict, total=False):
    success: bool
    stdout: str
    stderr: str
    error: str | None
    result: Any
    result_type: str | None
    result_kind: str
    result_name: str | None
    variables: dict[str, Any]
    artifacts: list[dict[str, Any]]


class CodeExecutionService(Protocol):
    async def execute(
        self,
        *,
        code: str,
        workspace_id: str,
        workspace_duckdb_path: str,
        timeout: int,
    ) -> ExecutionResult: ...

    async def get_status(self, *, workspace_id: str) -> str: ...


class LocalCodeExecutionService:
    """In-process execution service backed by the workspace kernel manager."""

    async def execute(
        self,
        *,
        code: str,
        workspace_id: str,
        workspace_duckdb_path: str,
        timeout: int,
    ) -> ExecutionResult:
        return await execute_code(
            code=code,
            timeout=timeout,
            workspace_id=workspace_id,
            workspace_duckdb_path=workspace_duckdb_path,
        )

    async def get_status(self, *, workspace_id: str) -> str:
        return await get_workspace_kernel_status(workspace_id)


_execution_service: CodeExecutionService = LocalCodeExecutionService()


def get_code_execution_service() -> CodeExecutionService:
    return _execution_service
