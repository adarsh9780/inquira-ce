"""API v1 runtime endpoints for workspace-scoped execution and schema."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import uuid
from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.code_executor import (
    bootstrap_workspace_runtime,
    delete_workspace_artifact_via_kernel,
    execute_code,
    get_workspace_artifact_metadata_via_kernel,
    get_workspace_artifact_usage_via_kernel,
    get_workspace_dataframe_rows,
    get_workspace_kernel_status,
    get_workspace_run_exports,
    interrupt_workspace_kernel,
    list_workspace_artifacts_via_kernel,
    reset_workspace_kernel,
)
from ...services.artifact_scratchpad import get_artifact_scratchpad_store
from ...services.output_capture import build_run_wrapped_code
from ..db.session import get_appdata_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_repository import WorkspaceRepository
from ..repositories.conversation_repository import ConversationRepository
from ..services.secret_storage_service import SecretStorageService
from ..services.conversation_service import ConversationService
from .deps import ensure_appdata_principal, get_current_user
from ...core.prompt_library import get_prompt
from ...services.llm_service import LLMService
from ...services.llm_runtime_config import load_llm_runtime_config
from ...services.execution_config import load_execution_runtime_config
from ...services.runner_env import install_runner_package
from ...services.terminal_executor import (
    run_workspace_terminal_command,
    stream_workspace_terminal_command,
    stop_workspace_terminal_session,
)
from ...services.websocket_manager import websocket_manager
from ...core.logger import logprint
from ..services.command_service import (
    CommandExecutionError,
    execute_workspace_command,
    list_command_definitions,
    parse_command_text,
)

router = APIRouter(tags=["V1 Runtime"], dependencies=[Depends(ensure_appdata_principal)])


def _default_variable_bundle() -> dict[str, dict[str, Any]]:
    return {"dataframes": {}, "figures": {}, "scalars": {}}


class ExecuteRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(60, ge=1, le=300, description="Max execution time in seconds")


class ExecuteResponse(BaseModel):
    success: bool
    run_id: str | None = None
    stdout: str = ""
    stderr: str = ""
    has_stdout: bool = False
    has_stderr: bool = False
    error: str | None = None
    result: object | None = None
    result_type: str | None = None
    result_kind: str = "none"
    result_name: str | None = None
    variables: dict[str, dict[str, Any]] = Field(
        default_factory=_default_variable_bundle
    )
    artifacts: list[dict[str, Any]] = Field(default_factory=list)


class DataframeArtifactRowsResponse(BaseModel):
    artifact_id: str
    name: str
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    offset: int
    limit: int


class ArtifactMetadataResponse(BaseModel):
    artifact_id: str
    run_id: str
    workspace_id: str
    logical_name: str
    kind: str
    pointer: str
    table_name: str | None = None
    schema_columns: list[dict[str, Any]] | None = Field(default=None, alias="schema")
    row_count: int | None = None
    payload: dict[str, Any] | None = None
    created_at: str
    expires_at: str
    status: str
    error: str | None = None


class WorkspaceArtifactSummary(BaseModel):
    artifact_id: str
    logical_name: str
    kind: str
    row_count: int | None = None
    columns: list[dict[str, Any]] | None = None
    created_at: str
    status: str


class WorkspaceArtifactListResponse(BaseModel):
    artifacts: list[WorkspaceArtifactSummary]
    total: int


class WorkspaceArtifactUsageResponse(BaseModel):
    workspace_id: str
    duckdb_bytes: int
    duckdb_warning_threshold_bytes: int
    figure_count: int
    figure_warning_threshold_count: int
    duckdb_warning: bool
    figure_warning: bool
    warning: bool


class ArtifactDeleteResponse(BaseModel):
    artifact_id: str
    deleted: bool


class TerminalExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Shell command to run")
    cwd: str | None = Field(default=None, description="Optional working directory override")
    timeout: int = Field(120, ge=1, le=600, description="Max command execution time in seconds")


class TerminalExecuteResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int
    cwd: str
    shell: str
    platform: str
    timed_out: bool = False
    persistent: bool = True


class TerminalSessionResetResponse(BaseModel):
    workspace_id: str
    reset: bool


class RunnerPackageInstallRequest(BaseModel):
    workspace_id: str
    package: str = Field(..., min_length=1, description="Package name without version specifier")
    version: str = Field(..., min_length=1, description="Exact package version")
    index_url: str | None = Field(default=None, description="Optional package index URL")
    save_as_default: bool = Field(
        default=False,
        description="Persist package/index settings to inquira.toml runner defaults",
    )


class RunnerPackageInstallResponse(BaseModel):
    installed: bool
    package_spec: str
    installer: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    workspace_kernel_reset: bool
    saved_as_default: bool


class KernelStatusResponse(BaseModel):
    workspace_id: str
    status: str


class KernelResetResponse(BaseModel):
    workspace_id: str
    reset: bool


class WorkspacePathsResponse(BaseModel):
    workspace_id: str
    workspace_dir: str
    duckdb_path: str
    terminal_enabled: bool = False


class WorkspaceColumnsResponse(BaseModel):
    columns: list[dict[str, str]]


class CommandCatalogResponse(BaseModel):
    commands: list[dict[str, str]]


class CommandExecuteRequest(BaseModel):
    text: str | None = None
    name: str | None = None
    raw_args: str = ""
    default_table: str | None = None
    conversation_id: str | None = None
    row_limit: int = Field(500, ge=1, le=2000)


class CommandExecuteResponse(BaseModel):
    command: str
    name: str
    output: str
    result_type: str = "message"
    result: dict[str, Any] | None = None
    truncated: bool = False
    conversation_id: str | None = None
    turn_id: str | None = None


class DatasetSchemaResponse(BaseModel):
    table_name: str
    context: str = ""
    columns: list[dict[str, Any]]


class SaveSchemaRequest(BaseModel):
    context: str = ""
    columns: list[dict[str, Any]]


class RegenerateSchemaRequest(BaseModel):
    context: str | None = None
    model: str | None = None


class SchemaDescriptionItem(BaseModel):
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)


class SchemaDescriptionList(BaseModel):
    schemas: list[SchemaDescriptionItem]


class SchemaListResponse(BaseModel):
    schemas: list[dict[str, Any]]


_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PACKAGE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")
_INSTALL_BLOCK_RE = re.compile(
    r"(?im)(?:^\s*!?\s*%?\s*pip\s+install\b|uv\s+pip\s+install\b|python\s+-m\s+pip\s+install\b)"
)
_DEFAULT_TERMINAL_DENYLIST = [
    r"(^|\\s)rm\\s+-rf\\s+/",
    r":\\(\\)\\s*\\{\\s*:\\|:\\s*&\\s*\\};:",
]
_DEFAULT_TERMINAL_ALLOWLIST = {
    "uv",
    "python",
    "python3",
    "py",
    "pip",
    "pip3",
    "ls",
    "grep",
    "cd",
    "pwd",
}
_BLOCKED_TERMINAL_SYNTAX_RE = re.compile(r"(&&|\|\||;|>|<|`|\$\(|\r|\n)")
_ARTIFACT_DUCKDB_WARNING_THRESHOLD_BYTES = 1024 * 1024 * 1024
_ARTIFACT_FIGURE_WARNING_THRESHOLD_COUNT = 20


def _normalize_table_name(raw: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()


def _normalize_schema_item_name(raw: str) -> str:
    return "".join(c for c in str(raw or "").strip().lower() if c.isalnum())


def _normalize_alias_list(raw: Any, *, max_items: int = 5) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        alias = str(item or "").strip()
        if not alias:
            continue
        dedupe = alias.lower()
        if dedupe in seen:
            continue
        seen.add(dedupe)
        normalized.append(alias)
        if len(normalized) >= max_items:
            break
    return normalized


def _validate_runner_install_request(
    payload: RunnerPackageInstallRequest,
    config: Any,
) -> tuple[str, str | None]:
    package_name = payload.package.strip()
    version = payload.version.strip()
    index_url = (payload.index_url or "").strip() or None

    if not _PACKAGE_NAME_RE.fullmatch(package_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid package name. Use letters, numbers, dot, underscore, or hyphen only.",
        )
    if not _PACKAGE_VERSION_RE.fullmatch(version):
        raise HTTPException(
            status_code=400,
            detail="Invalid package version. Exact pinned versions only (e.g., 2.2.3).",
        )
    if any(token in package_name for token in ["<", ">", "=", "!", "~", " "]):
        raise HTTPException(status_code=400, detail="Package name must not include a version specifier.")
    if any(token in version for token in ["<", ">", "=", "!", "~", " "]):
        raise HTTPException(status_code=400, detail="Version must be exact and must not include comparison operators.")

    if index_url and not (index_url.startswith("http://") or index_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="index_url must start with http:// or https://")

    allowlist = [p.strip().lower() for p in (config.runner_package_allowlist or []) if p.strip()]
    denylist = [p.strip().lower() for p in (config.runner_package_denylist or []) if p.strip()]
    package_lower = package_name.lower()

    if allowlist and package_lower not in allowlist:
        raise HTTPException(status_code=403, detail="Package is not allowed by runner package policy.")
    if package_lower in denylist:
        raise HTTPException(status_code=403, detail="Package is blocked by runner package policy.")

    max_packages = max(1, int(config.runner_install_max_packages_per_request or 1))
    if max_packages < 1:
        raise HTTPException(status_code=400, detail="Runner install policy is misconfigured.")

    package_spec = f"{package_name}=={version}"
    return package_spec, index_url


def _runner_toml_path() -> Path:
    cfg_path = os.getenv("INQUIRA_TOML_PATH")
    if cfg_path:
        return Path(cfg_path)
    return Path(__file__).resolve().parents[4] / "inquira.toml"


def _persist_runner_defaults(package_spec: str, index_url: str | None) -> None:
    path = _runner_toml_path()
    if not path.exists():
        raise RuntimeError(f"Cannot persist runner defaults; config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    section_start = None
    section_end = len(lines)
    for idx, line in enumerate(lines):
        if line.strip() == "[execution.runner]":
            section_start = idx
            break

    if section_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[execution.runner]")
        lines.append('packages = []')
        section_start = len(lines) - 2
        section_end = len(lines)
    else:
        for idx in range(section_start + 1, len(lines)):
            if lines[idx].strip().startswith("["):
                section_end = idx
                break

    section_lines = lines[section_start + 1 : section_end]
    packages_idx = None
    index_url_idx = None
    for idx, line in enumerate(section_lines):
        stripped = line.strip()
        if stripped.startswith("packages"):
            packages_idx = idx
        if stripped.startswith("index-url"):
            index_url_idx = idx

    runtime = load_execution_runtime_config()
    merged_packages = list(runtime.runner_packages or [])
    if package_spec not in merged_packages:
        merged_packages.append(package_spec)
    packages_value = "[" + ", ".join(f'"{pkg}"' for pkg in merged_packages) + "]"
    packages_line = f"packages = {packages_value}"

    if packages_idx is None:
        section_lines.append(packages_line)
    else:
        section_lines[packages_idx] = packages_line

    if index_url:
        index_line = f'index-url = "{index_url}"'
        if index_url_idx is None:
            section_lines.append(index_line)
        else:
            section_lines[index_url_idx] = index_line

    lines[section_start + 1 : section_end] = section_lines
    updated = "\n".join(lines).rstrip() + "\n"
    path.write_text(updated, encoding="utf-8")


def _normalize_schema_columns(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _table_exists_in_workspace_db(duckdb_path: str, table_name: str) -> bool:
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        row = con.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'main' AND lower(table_name) = ?
            LIMIT 1
            """,
            [table_name.lower()],
        ).fetchone()
        return row is not None
    finally:
        con.close()


def _read_workspace_columns(duckdb_path: str) -> list[dict[str, str]]:
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        rows = con.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
    finally:
        con.close()

    return [
        {
            "table_name": str(row[0]),
            "column_name": str(row[1]),
            "dtype": str(row[2] or ""),
        }
        for row in rows
    ]


def _read_table_columns_for_prompt(
    duckdb_path: str,
    table_name: str,
    allow_sample_values: bool,
) -> list[dict[str, Any]]:
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        rows = con.execute(f'DESCRIBE "{table_name}"').fetchall()
        columns: list[dict[str, Any]] = []
        for row in rows:
            col_name = str(row[0])
            col_dtype = str(row[1])
            samples: list[Any] = []
            if allow_sample_values:
                sample_rows = con.execute(
                    f'SELECT DISTINCT "{col_name}" FROM "{table_name}" LIMIT 10'
                ).fetchall()
                samples = [s[0] for s in sample_rows]
            columns.append(
                {
                    "name": col_name,
                    "dtype": col_dtype,
                    "samples": samples,
                    "description": "",
                    "aliases": [],
                }
            )
        return columns
    finally:
        con.close()


def _read_columns_from_schema_file(
    schema_path: str,
    allow_sample_values: bool,
) -> list[dict[str, Any]]:
    path = Path(schema_path)
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    raw_columns = payload.get("columns", [])
    if not isinstance(raw_columns, list):
        return []

    columns: list[dict[str, Any]] = []
    for col in raw_columns:
        if not isinstance(col, dict):
            continue
        name = str(col.get("name", "")).strip()
        if not name:
            continue
        columns.append(
            {
                "name": name,
                "dtype": str(col.get("dtype") or col.get("type") or "VARCHAR"),
                "samples": (
                    col.get("samples", [])
                    if allow_sample_values and isinstance(col.get("samples", []), list)
                    else []
                ),
                "description": str(col.get("description", "")),
                "aliases": _normalize_alias_list(col.get("aliases", [])),
            }
        )
    return columns


async def _require_workspace_access(
    session: AsyncSession,
    user_id: str,
    workspace_id: str,
):
    workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _derive_command_conversation_title(command_text: str) -> str:
    compact = " ".join(str(command_text or "").strip().split())
    if not compact:
        return "New Conversation"
    if len(compact) <= 80:
        return compact
    return compact[:77].rstrip() + "..."


async def _resolve_or_create_command_conversation(
    *,
    session: AsyncSession,
    principal_id: str,
    workspace_id: str,
    conversation_id: str | None,
    command_text: str,
):
    candidate = str(conversation_id or "").strip()
    if candidate:
        conversation = await ConversationRepository.get_conversation(session, candidate)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if str(conversation.workspace_id) != str(workspace_id):
            raise HTTPException(
                status_code=400,
                detail="Conversation does not belong to the selected workspace.",
            )
        return conversation

    return await ConversationService.create_conversation(
        session=session,
        principal_id=principal_id,
        workspace_id=workspace_id,
        title=_derive_command_conversation_title(command_text),
    )


async def _persist_command_turn(
    *,
    session: AsyncSession,
    conversation: Any,
    command_text: str,
    command_name: str,
    command_output: str,
    command_result_type: str,
    command_result: dict[str, Any] | None,
    truncated: bool,
) -> str:
    conversation_id = str(getattr(conversation, "id", "") or "").strip()
    if not conversation_id:
        raise HTTPException(status_code=500, detail="Conversation initialization failed")

    seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
    if seq_no == 1 and (str(getattr(conversation, "title", "") or "").strip().lower() == "new conversation"):
        conversation.title = _derive_command_conversation_title(command_text)

    assistant_text = str(command_output or "").strip() or f"Executed /{command_name}."
    metadata: dict[str, Any] = {
        "source": "slash_command",
        "command_name": str(command_name or ""),
        "result_type": str(command_result_type or "message"),
        "truncated": bool(truncated),
    }
    if isinstance(command_result, dict):
        columns = command_result.get("columns")
        row_count = command_result.get("row_count")
        metadata["result"] = {
            "columns": [str(col) for col in columns[:20]] if isinstance(columns, list) else [],
            "row_count": int(row_count) if isinstance(row_count, int) else None,
        }

    turn = await ConversationRepository.create_turn(
        session=session,
        conversation_id=conversation_id,
        seq_no=seq_no,
        user_text=str(command_text or ""),
        assistant_text=assistant_text,
        tool_events=None,
        metadata=metadata,
        code_snapshot=None,
    )
    await session.commit()
    return str(turn.id)


async def _persist_failed_command_turn_best_effort(
    *,
    session: AsyncSession,
    principal_id: str,
    workspace_id: str,
    conversation_id: str | None,
    command_text: str,
    command_name: str,
    error_detail: str,
) -> None:
    try:
        conversation = await _resolve_or_create_command_conversation(
            session=session,
            principal_id=principal_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            command_text=command_text,
        )
        await _persist_command_turn(
            session=session,
            conversation=conversation,
            command_text=command_text,
            command_name=command_name,
            command_output=f"Command failed: {error_detail}",
            command_result_type="error",
            command_result={"error": error_detail},
            truncated=False,
        )
    except Exception as exc:
        logprint(
            "Failed to persist slash-command error turn",
            level="WARNING",
            workspace_id=workspace_id,
            command=command_text,
            error=str(exc),
        )


def _workspace_db_missing_detail(duckdb_path: str) -> str:
    return (
        "Workspace database is missing.\n"
        f"Expected path: {duckdb_path}\n"
        "Please re-create the workspace data by selecting the original dataset again."
    )


def _is_managed_workspace_path(duckdb_path: str) -> bool:
    parts = {part.lower() for part in Path(str(duckdb_path or "")).expanduser().parts}
    return ".inquira" in parts and "workspaces" in parts


def _ensure_workspace_db_exists_or_raise(duckdb_path: str) -> None:
    resolved = Path(str(duckdb_path or "")).expanduser()
    if resolved.exists():
        return
    if not _is_managed_workspace_path(str(resolved)):
        return
    raise HTTPException(status_code=409, detail=_workspace_db_missing_detail(str(resolved)))


def _build_inline_artifact_fallback(
    *,
    run_id: str,
    execution_result: dict[str, Any],
) -> list[dict[str, Any]]:
    result = execution_result.get("result")
    result_type = str(execution_result.get("result_type") or "").lower()
    if result_type != "dataframe":
        return []
    if not isinstance(result, dict):
        return []
    columns = result.get("columns")
    rows = result.get("data")
    if not isinstance(columns, list) or not isinstance(rows, list):
        return []

    column_names = [str(col) for col in columns]
    preview_rows: list[dict[str, Any]] = []
    for row in rows[:25]:
        if isinstance(row, dict):
            preview_rows.append({str(key): value for key, value in row.items()})
            continue
        if isinstance(row, list):
            mapped = {
                str(column_names[idx]): row[idx]
                for idx in range(min(len(column_names), len(row)))
            }
            preview_rows.append(mapped)

    return [
        {
            "artifact_id": None,
            "run_id": run_id,
            "kind": "dataframe",
            "pointer": None,
            "logical_name": "result",
            "row_count": len(rows),
            "schema": [{"name": str(col), "dtype": ""} for col in column_names],
            "preview_rows": preview_rows,
            "created_at": "",
            "expires_at": "",
            "status": "ready",
            "error": None,
            "table_name": None,
        }
    ]


@router.get("/workspaces/{workspace_id}/paths", response_model=WorkspacePathsResponse)
async def get_workspace_paths(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    workspace_path = Path(workspace.duckdb_path).parent
    runtime = load_execution_runtime_config()
    return WorkspacePathsResponse(
        workspace_id=workspace_id,
        workspace_dir=str(workspace_path),
        duckdb_path=str(workspace.duckdb_path),
        terminal_enabled=bool(runtime.terminal_enabled),
    )


@router.get("/workspaces/{workspace_id}/columns", response_model=WorkspaceColumnsResponse)
async def get_workspace_columns(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    _ensure_workspace_db_exists_or_raise(str(workspace.duckdb_path))
    try:
        columns = await asyncio.to_thread(_read_workspace_columns, str(workspace.duckdb_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load workspace columns: {str(exc)}") from exc
    return WorkspaceColumnsResponse(columns=columns)


@router.get("/workspaces/{workspace_id}/commands", response_model=CommandCatalogResponse)
async def list_workspace_commands(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    await _require_workspace_access(session, current_user.id, workspace_id)
    return CommandCatalogResponse(commands=list_command_definitions())


@router.post("/workspaces/{workspace_id}/commands/execute", response_model=CommandExecuteResponse)
async def execute_workspace_slash_command(
    workspace_id: str,
    payload: CommandExecuteRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    _ensure_workspace_db_exists_or_raise(str(workspace.duckdb_path))

    parsed_name = ""
    raw_args = ""
    args: list[str] = []
    command_text = str(payload.text or "").strip()

    if command_text:
        try:
            parsed_name, raw_args, args = parse_command_text(command_text)
        except CommandExecutionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        parsed_name = str(payload.name or "").strip().lower()
        raw_args = str(payload.raw_args or "").strip()
        if not parsed_name:
            raise HTTPException(status_code=400, detail="Provide either command text or command name.")
        try:
            args = shlex.split(raw_args) if raw_args else []
        except ValueError:
            args = raw_args.split()
        command_text = f"/{parsed_name}" + (f" {raw_args}" if raw_args else "")

    try:
        result = await asyncio.to_thread(
            execute_workspace_command,
            duckdb_path=str(workspace.duckdb_path),
            name=parsed_name,
            args=args,
            default_table=payload.default_table,
            row_limit=payload.row_limit,
        )
    except CommandExecutionError as exc:
        await _persist_failed_command_turn_best_effort(
            session=session,
            principal_id=str(current_user.id),
            workspace_id=workspace_id,
            conversation_id=payload.conversation_id,
            command_text=command_text,
            command_name=parsed_name or "command",
            error_detail=str(exc),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except duckdb.Error as exc:
        detail = f"Command execution failed: {str(exc)}"
        await _persist_failed_command_turn_best_effort(
            session=session,
            principal_id=str(current_user.id),
            workspace_id=workspace_id,
            conversation_id=payload.conversation_id,
            command_text=command_text,
            command_name=parsed_name or "command",
            error_detail=detail,
        )
        raise HTTPException(status_code=400, detail=f"Command execution failed: {str(exc)}") from exc
    except Exception as exc:
        detail = f"Command execution failed: {str(exc)}"
        await _persist_failed_command_turn_best_effort(
            session=session,
            principal_id=str(current_user.id),
            workspace_id=workspace_id,
            conversation_id=payload.conversation_id,
            command_text=command_text,
            command_name=parsed_name or "command",
            error_detail=detail,
        )
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(exc)}") from exc

    conversation = await _resolve_or_create_command_conversation(
        session=session,
        principal_id=str(current_user.id),
        workspace_id=workspace_id,
        conversation_id=payload.conversation_id,
        command_text=command_text,
    )

    turn_id = await _persist_command_turn(
        session=session,
        conversation=conversation,
        command_text=command_text,
        command_name=str(result.get("name") or parsed_name),
        command_output=str(result.get("output") or ""),
        command_result_type=str(result.get("result_type") or "message"),
        command_result=result.get("result") if isinstance(result.get("result"), dict) else None,
        truncated=bool(result.get("truncated")),
    )

    return CommandExecuteResponse(
        command=command_text,
        name=str(result.get("name") or parsed_name),
        output=str(result.get("output") or ""),
        result_type=str(result.get("result_type") or "message"),
        result=result.get("result") if isinstance(result.get("result"), dict) else None,
        truncated=bool(result.get("truncated")),
        conversation_id=str(getattr(conversation, "id", "") or ""),
        turn_id=turn_id,
    )


@router.post("/workspaces/{workspace_id}/execute", response_model=ExecuteResponse)
async def execute_workspace_code(
    workspace_id: str,
    payload: ExecuteRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    _ensure_workspace_db_exists_or_raise(str(workspace.duckdb_path))
    if _INSTALL_BLOCK_RE.search(payload.code or ""):
        raise HTTPException(
            status_code=400,
            detail=(
                "Package installation commands are blocked in analysis execution. "
                "Use Settings > Runner Packages to install pinned dependencies."
            ),
        )
    run_id = str(uuid.uuid4())
    wrapped_code = build_run_wrapped_code(payload.code, run_id, [])
    result = await execute_code(
        code=wrapped_code,
        timeout=payload.timeout,
        working_dir=str(Path(workspace.duckdb_path).parent),
        workspace_id=workspace_id,
        workspace_duckdb_path=str(workspace.duckdb_path),
    )
    artifacts = [
        item for item in (result.get("artifacts") or []) if isinstance(item, dict)
    ]
    if not artifacts:
        try:
            exports = await get_workspace_run_exports(
                workspace_id=workspace_id,
                run_id=run_id,
            )
            artifacts = [item for item in exports if isinstance(item, dict)]
        except Exception:
            artifacts = []
    if not artifacts:
        artifacts = _build_inline_artifact_fallback(
            run_id=run_id,
            execution_result=result,
        )
    result["run_id"] = run_id
    result["artifacts"] = artifacts
    return ExecuteResponse(**result)


@router.get(
    "/workspaces/{workspace_id}/artifacts/dataframes/{artifact_id}/rows",
    response_model=DataframeArtifactRowsResponse,
)
async def get_workspace_dataframe_artifact_rows(
    workspace_id: str,
    artifact_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=1000),
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    rows: dict[str, Any] | None = None
    try:
        rows = store.get_dataframe_rows(
            workspace_duckdb_path=str(workspace.duckdb_path),
            artifact_id=artifact_id,
            offset=offset,
            limit=limit,
        )
    except duckdb.IOException as exc:
        message = str(exc)
        if "Conflicting lock is held" not in message:
            raise HTTPException(status_code=503, detail=f"Artifact store unavailable: {message}") from exc
        # Kernel path shares the in-process scratchpad connection, so use it as lock-safe fallback.
        rows = await get_workspace_dataframe_rows(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            offset=offset,
            limit=limit,
        )
    if rows is None:
        raise HTTPException(status_code=404, detail="Dataframe artifact not found")
    return DataframeArtifactRowsResponse(**rows)


@router.get(
    "/workspaces/{workspace_id}/artifacts/{artifact_id}/rows",
    response_model=DataframeArtifactRowsResponse,
)
async def get_workspace_artifact_rows(
    workspace_id: str,
    artifact_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=1000),
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    rows: dict[str, Any] | None = None
    try:
        rows = store.get_dataframe_rows(
            workspace_duckdb_path=str(workspace.duckdb_path),
            artifact_id=artifact_id,
            offset=offset,
            limit=limit,
        )
    except duckdb.IOException as exc:
        message = str(exc)
        if "Conflicting lock is held" not in message:
            raise HTTPException(status_code=503, detail=f"Artifact store unavailable: {message}") from exc
        rows = await get_workspace_dataframe_rows(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
            offset=offset,
            limit=limit,
        )
    if rows is None:
        raise HTTPException(status_code=404, detail="Artifact rows not found")
    return DataframeArtifactRowsResponse(**rows)


@router.get(
    "/workspaces/{workspace_id}/artifacts/usage",
    response_model=WorkspaceArtifactUsageResponse,
)
async def get_workspace_artifact_usage(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Return scratchpad usage summary used by status-bar artifact pressure warning."""
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    try:
        usage = store.get_workspace_artifact_usage(
            workspace_duckdb_path=str(workspace.duckdb_path),
        )
    except duckdb.IOException as exc:
        if "Conflicting lock is held" not in str(exc):
            raise HTTPException(status_code=503, detail=f"Artifact usage unavailable: {exc}") from exc
        usage = await get_workspace_artifact_usage_via_kernel(workspace_id)

    duckdb_bytes = max(0, int(usage.get("duckdb_bytes") or 0))
    figure_count = max(0, int(usage.get("figure_count") or 0))
    duckdb_warning = duckdb_bytes > _ARTIFACT_DUCKDB_WARNING_THRESHOLD_BYTES
    figure_warning = figure_count > _ARTIFACT_FIGURE_WARNING_THRESHOLD_COUNT
    return WorkspaceArtifactUsageResponse(
        workspace_id=workspace_id,
        duckdb_bytes=duckdb_bytes,
        duckdb_warning_threshold_bytes=_ARTIFACT_DUCKDB_WARNING_THRESHOLD_BYTES,
        figure_count=figure_count,
        figure_warning_threshold_count=_ARTIFACT_FIGURE_WARNING_THRESHOLD_COUNT,
        duckdb_warning=duckdb_warning,
        figure_warning=figure_warning,
        warning=duckdb_warning or figure_warning,
    )


@router.get(
    "/workspaces/{workspace_id}/artifacts/{artifact_id}",
    response_model=ArtifactMetadataResponse,
)
async def get_workspace_artifact_metadata(
    workspace_id: str,
    artifact_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    artifact: dict[str, Any] | None = None
    try:
        artifact = store.get_artifact(
            workspace_duckdb_path=str(workspace.duckdb_path),
            artifact_id=artifact_id,
        )
    except duckdb.IOException as exc:
        message = str(exc)
        if "Conflicting lock is held" not in message:
            raise HTTPException(status_code=503, detail=f"Artifact store unavailable: {message}") from exc
        # Lock-safe fallback: query through the kernel's in-process scratchpad connection.
        artifact = await get_workspace_artifact_metadata_via_kernel(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactMetadataResponse(**artifact)


@router.delete(
    "/workspaces/{workspace_id}/artifacts/{artifact_id}",
    response_model=ArtifactDeleteResponse,
)
async def delete_workspace_artifact(
    workspace_id: str,
    artifact_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    deleted = False
    try:
        deleted = store.delete_artifact(
            workspace_duckdb_path=str(workspace.duckdb_path),
            artifact_id=artifact_id,
        )
    except duckdb.IOException as exc:
        message = str(exc)
        if "Conflicting lock is held" not in message:
            raise HTTPException(status_code=503, detail=f"Artifact store unavailable: {message}") from exc
        deleted = await delete_workspace_artifact_via_kernel(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return ArtifactDeleteResponse(artifact_id=artifact_id, deleted=True)


@router.get(
    "/workspaces/{workspace_id}/artifacts",
    response_model=WorkspaceArtifactListResponse,
)
async def list_workspace_artifacts(
    workspace_id: str,
    kind: str | None = Query(default=None, description="Filter by artifact kind, e.g. 'dataframe' or 'figure'"),
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """List all non-expired artifacts for a workspace, optionally filtered by kind."""
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    store = get_artifact_scratchpad_store()
    try:
        items = store.list_artifacts_for_workspace(
            workspace_duckdb_path=str(workspace.duckdb_path),
            kind=kind,
        )
    except duckdb.IOException as exc:
        if "Conflicting lock is held" not in str(exc):
            raise HTTPException(status_code=503, detail=f"Artifact store unavailable: {exc}") from exc
        # Lock-safe fallback: query through the kernel's in-process scratchpad connection.
        items = await list_workspace_artifacts_via_kernel(workspace_id, kind=kind)
    summaries = [
        WorkspaceArtifactSummary(
            artifact_id=item["artifact_id"],
            logical_name=item["logical_name"],
            kind=item["kind"],
            row_count=item.get("row_count"),
            columns=item.get("schema"),
            created_at=item["created_at"],
            status=item["status"],
        )
        for item in items
    ]
    return WorkspaceArtifactListResponse(artifacts=summaries, total=len(summaries))


@router.post("/runtime/runner/packages/install", response_model=RunnerPackageInstallResponse)
async def install_runner_runtime_package(
    payload: RunnerPackageInstallRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, payload.workspace_id)
    runtime = load_execution_runtime_config()
    package_spec, index_url = _validate_runner_install_request(payload, runtime)

    try:
        install_result = await asyncio.to_thread(
            install_runner_package,
            runtime,
            package_spec,
            index_url,
            str(workspace.duckdb_path),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    reset = await reset_workspace_kernel(payload.workspace_id)

    saved_default = False
    if payload.save_as_default:
        try:
            await asyncio.to_thread(_persist_runner_defaults, package_spec, index_url)
            load_execution_runtime_config.cache_clear()
            saved_default = True
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Package installed but failed to persist runner defaults: {str(exc)}",
            ) from exc

    return RunnerPackageInstallResponse(
        installed=True,
        package_spec=package_spec,
        installer=install_result.installer,
        command=install_result.command,
        stdout=install_result.stdout,
        stderr=install_result.stderr,
        workspace_kernel_reset=reset,
        saved_as_default=saved_default,
    )


@router.post(
    "/workspaces/{workspace_id}/terminal/execute",
    response_model=TerminalExecuteResponse,
)
async def execute_workspace_terminal_command(
    workspace_id: str,
    payload: TerminalExecuteRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    runtime = load_execution_runtime_config()
    _enforce_terminal_enabled(runtime)
    _enforce_terminal_command_policy(payload.command, runtime)
    workspace_dir = str(Path(workspace.duckdb_path).parent)
    _validate_terminal_cwd(payload.cwd, workspace_dir)
    try:
        result = await run_workspace_terminal_command(
            user_id=current_user.id,
            workspace_id=workspace_id,
            command=payload.command,
            workspace_dir=workspace_dir,
            cwd=payload.cwd,
            timeout=payload.timeout,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logprint(
        "Terminal command completed",
        level="INFO",
        workspace_id=workspace_id,
        user_id=current_user.id,
        exit_code=result.get("exit_code"),
        timed_out=result.get("timed_out"),
    )
    return TerminalExecuteResponse(**result)


@router.post("/workspaces/{workspace_id}/terminal/stream")
async def stream_workspace_terminal_command_sse(
    workspace_id: str,
    payload: TerminalExecuteRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    runtime = load_execution_runtime_config()
    _enforce_terminal_enabled(runtime)
    _enforce_terminal_command_policy(payload.command, runtime)
    workspace_dir = str(Path(workspace.duckdb_path).parent)
    _validate_terminal_cwd(payload.cwd, workspace_dir)

    async def event_stream():
        yield _format_sse_event("status", {"message": "Command started"})
        try:
            async for event in stream_workspace_terminal_command(
                user_id=current_user.id,
                workspace_id=workspace_id,
                command=payload.command,
                workspace_dir=workspace_dir,
                cwd=payload.cwd,
                timeout=payload.timeout,
            ):
                event_type = str(event.get("type") or "")
                if event_type == "output":
                    yield _format_sse_event("output", {"line": str(event.get("line") or "")})
                elif event_type == "error":
                    yield _format_sse_event("error", {"detail": str(event.get("error") or "Terminal execution failed.")})
                    return
                elif event_type == "final":
                    result = event.get("result") or {}
                    yield _format_sse_event("final", result)
                    return
        except (ValueError, PermissionError) as exc:
            yield _format_sse_event("error", {"detail": str(exc)})
            return
        except Exception as exc:
            yield _format_sse_event("error", {"detail": str(exc)})
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/workspaces/{workspace_id}/terminal/session/reset",
    response_model=TerminalSessionResetResponse,
)
async def reset_workspace_terminal_session(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    runtime = load_execution_runtime_config()
    _enforce_terminal_enabled(runtime)
    await _require_workspace_access(session, current_user.id, workspace_id)
    reset = await stop_workspace_terminal_session(
        user_id=current_user.id,
        workspace_id=workspace_id,
    )
    return TerminalSessionResetResponse(workspace_id=workspace_id, reset=reset)


@router.get(
    "/workspaces/{workspace_id}/kernel/status",
    response_model=KernelStatusResponse,
)
async def get_workspace_kernel_runtime_status(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Return current workspace kernel status."""
    await _require_workspace_access(session, current_user.id, workspace_id)
    status = await get_workspace_kernel_status(workspace_id)
    return KernelStatusResponse(workspace_id=workspace_id, status=status)


@router.post(
    "/workspaces/{workspace_id}/runtime/bootstrap",
    response_model=KernelResetResponse,
)
async def bootstrap_workspace_runtime_endpoint(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    _ensure_workspace_db_exists_or_raise(str(workspace.duckdb_path))
    websocket_user_id = _resolve_websocket_user_id(current_user.id)

    async def _progress(stage: str, message: str) -> None:
        if websocket_user_id:
            await websocket_manager.send_to_user(
                websocket_user_id,
                {
                    "type": "progress",
                    "stage": stage,
                    "message": message,
                },
            )
        logprint(
            f"Workspace runtime bootstrap [{workspace_id}] {stage}: {message}",
            level="info",
        )

    try:
        await _progress("workspace_runtime_start", f"Preparing runtime for workspace {workspace_id}...")
        ready = await bootstrap_workspace_runtime(
            workspace_id=workspace_id,
            workspace_duckdb_path=str(workspace.duckdb_path),
            progress_callback=_progress,
        )
        if websocket_user_id:
            await websocket_manager.send_to_user(
                websocket_user_id,
                {
                    "type": "completed",
                    "result": {
                        "workspace_id": workspace_id,
                        "status": "ready" if ready else "not_ready",
                    },
                },
            )
    except Exception as exc:
        detail = _describe_exception(exc)
        if websocket_user_id:
            await websocket_manager.send_error(
                websocket_user_id,
                f"Workspace runtime bootstrap failed: {detail}",
            )
        raise HTTPException(status_code=500, detail=detail) from exc
    return KernelResetResponse(workspace_id=workspace_id, reset=bool(ready))


@router.post(
    "/workspaces/{workspace_id}/kernel/interrupt",
    response_model=KernelResetResponse,
)
async def interrupt_workspace_kernel_runtime(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Interrupt currently running code in workspace kernel."""
    await _require_workspace_access(session, current_user.id, workspace_id)
    interrupted = await interrupt_workspace_kernel(workspace_id)
    return KernelResetResponse(workspace_id=workspace_id, reset=interrupted)


@router.post(
    "/workspaces/{workspace_id}/kernel/reset",
    response_model=KernelResetResponse,
)
async def reset_workspace_kernel_runtime(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Reset workspace kernel and clear in-memory execution context."""
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    return await _restart_workspace_kernel(workspace_id, workspace)


@router.post(
    "/workspaces/{workspace_id}/kernel/restart",
    response_model=KernelResetResponse,
)
async def restart_workspace_kernel_runtime(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Restart workspace kernel and warm it immediately."""
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    return await _restart_workspace_kernel(workspace_id, workspace)


async def _restart_workspace_kernel(workspace_id: str, workspace: Any) -> KernelResetResponse:
    """Shared reset/restart flow: reset session then warm-start kernel."""
    _ensure_workspace_db_exists_or_raise(str(workspace.duckdb_path))
    await reset_workspace_kernel(workspace_id)
    try:
        ready = await bootstrap_workspace_runtime(
            workspace_id=workspace_id,
            workspace_duckdb_path=str(workspace.duckdb_path),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return KernelResetResponse(workspace_id=workspace_id, reset=bool(ready))


@router.get(
    "/workspaces/{workspace_id}/datasets/{table_name}/schema",
    response_model=DatasetSchemaResponse,
)
async def get_workspace_dataset_schema(
    workspace_id: str,
    table_name: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    normalized = _normalize_table_name(table_name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid table name")

    dataset = await DatasetRepository.get_for_workspace_table(
        session=session,
        workspace_id=workspace_id,
        table_name=normalized,
    )
    if dataset is None and not _table_exists_in_workspace_db(workspace.duckdb_path, normalized):
        raise HTTPException(status_code=404, detail="Dataset table not found")

    if dataset is not None and dataset.schema_path:
        schema_path = Path(dataset.schema_path)
        if schema_path.exists():
            try:
                with schema_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return DatasetSchemaResponse(
                    table_name=normalized,
                    context=str(data.get("context", "")),
                    columns=_normalize_schema_columns(data.get("columns", [])),
                )
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                # Fall back to DuckDB introspection when saved schema metadata is unreadable.
                pass

    con = duckdb.connect(workspace.duckdb_path, read_only=True)
    try:
        rows = con.execute(f'DESCRIBE "{normalized}"').fetchall()
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "Dataset schema unavailable. The saved schema metadata is invalid "
                "and table introspection failed."
            ),
        ) from exc
    finally:
        con.close()

    columns = [
        {
            "name": row[0],
            "dtype": row[1],
            "description": "",
            "samples": [],
            "aliases": [],
        }
        for row in rows
    ]
    return DatasetSchemaResponse(table_name=normalized, context="", columns=columns)


@router.post(
    "/workspaces/{workspace_id}/datasets/{table_name}/schema",
    response_model=DatasetSchemaResponse,
)
async def save_workspace_dataset_schema(
    workspace_id: str,
    table_name: str,
    payload: SaveSchemaRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    normalized = _normalize_table_name(table_name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid table name")

    dataset = await DatasetRepository.get_for_workspace_table(
        session=session,
        workspace_id=workspace_id,
        table_name=normalized,
    )

    meta_dir = Path(workspace.duckdb_path).parent / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    schema_path = (
        Path(dataset.schema_path)
        if dataset is not None and dataset.schema_path
        else meta_dir / f"{normalized}_schema.json"
    )
    schema_columns: list[dict[str, Any]] = _normalize_schema_columns(payload.columns)
    schema_doc = {
        "table_name": normalized,
        "context": payload.context or "",
        "columns": schema_columns,
    }
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema_doc, f, indent=2)

    if dataset is not None:
        dataset.schema_path = str(schema_path)
        await session.commit()

    return DatasetSchemaResponse(
        table_name=normalized,
        context=str(schema_doc.get("context", "")),
        columns=schema_columns,
    )


@router.post(
    "/workspaces/{workspace_id}/datasets/{table_name}/schema/regenerate",
    response_model=DatasetSchemaResponse,
)
async def regenerate_workspace_dataset_schema(
    workspace_id: str,
    table_name: str,
    payload: RegenerateSchemaRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    normalized = _normalize_table_name(table_name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid table name")

    dataset = await DatasetRepository.get_for_workspace_table(
        session=session,
        workspace_id=workspace_id,
        table_name=normalized,
    )
    if dataset is None and not _table_exists_in_workspace_db(workspace.duckdb_path, normalized):
        raise HTTPException(status_code=404, detail="Dataset table not found")

    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    context = (payload.context if payload.context is not None else prefs.schema_context) or "General data analysis"
    model = (payload.model or prefs.selected_model or "google/gemini-2.5-flash").strip()
    allow_sample_values = bool(prefs.allow_schema_sample_values)

    try:
        api_key = SecretStorageService.get_api_key(current_user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="API key not set. Please configure your API key in Settings.",
        )

    columns: list[dict[str, Any]] = []
    try:
        columns = await asyncio.to_thread(
            _read_table_columns_for_prompt,
            workspace.duckdb_path,
            normalized,
            allow_sample_values,
        )
    except Exception:
        columns = []

    if (
        not columns
        and dataset is not None
        and dataset.schema_path
    ):
        columns = await asyncio.to_thread(
            _read_columns_from_schema_file,
            dataset.schema_path,
            allow_sample_values,
        )

    if not columns:
        raise HTTPException(status_code=400, detail="No columns found for this dataset table")

    columns_text = "\n".join(
        [f"- {col['name']} ({col['dtype']}): {(col.get('samples') or [])[:3]}" for col in columns]
    )
    prompt = get_prompt("schema_generation", context=context, columns_text=columns_text)

    llm_service = LLMService(api_key=api_key, model=model)
    runtime = load_llm_runtime_config()
    try:
        schema_response = await asyncio.to_thread(
            llm_service.ask,
            prompt,
            SchemaDescriptionList,
            runtime.schema_max_tokens,
        )
    except HTTPException as exc:
        detail = exc.detail if getattr(exc, "detail", None) is not None else str(exc)
        raise HTTPException(
            status_code=int(getattr(exc, "status_code", 500) or 500),
            detail=f"Failed to generate schema via LLM: {detail}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate schema via LLM: {str(exc)}"
        ) from exc

    generated_items = (
        schema_response.schemas
        if hasattr(schema_response, "schemas")
        else (schema_response if isinstance(schema_response, list) else [])
    )
    generated_by_name: dict[str, dict[str, Any]] = {}
    generated_by_normalized_name: dict[str, dict[str, Any]] = {}
    for item in generated_items:
        name = str(getattr(item, "name", "")).strip()
        description = str(getattr(item, "description", "")).strip()
        aliases = _normalize_alias_list(getattr(item, "aliases", []))
        if not name:
            continue
        payload = {"description": description, "aliases": aliases}
        generated_by_name[name] = payload
        normalized_name = _normalize_schema_item_name(name)
        if normalized_name and normalized_name not in generated_by_normalized_name:
            generated_by_normalized_name[normalized_name] = payload

    merged_columns = [
        {
            "name": col["name"],
            "dtype": col["dtype"],
            "description": (
                str(generated_by_name.get(col["name"], {}).get("description", "")).strip()
                or str(
                    generated_by_normalized_name.get(
                        _normalize_schema_item_name(col["name"]),
                        {},
                    ).get("description", "")
                ).strip()
                or str(col.get("description", "")).strip()
            ),
            "samples": col.get("samples", []),
            "aliases": (
                _normalize_alias_list(generated_by_name.get(col["name"], {}).get("aliases", []))
                or _normalize_alias_list(
                    generated_by_normalized_name.get(
                        _normalize_schema_item_name(col["name"]),
                        {},
                    ).get("aliases", [])
                )
                or _normalize_alias_list(col.get("aliases", []))
            ),
        }
        for col in columns
    ]

    meta_dir = Path(workspace.duckdb_path).parent / "meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    schema_path = (
        Path(dataset.schema_path)
        if dataset is not None and dataset.schema_path
        else meta_dir / f"{normalized}_schema.json"
    )
    schema_doc = {
        "table_name": normalized,
        "context": context,
        "columns": merged_columns,
    }
    from datetime import date, datetime
    
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)

    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema_doc, f, indent=2, cls=DateTimeEncoder)

    if dataset is not None:
        dataset.schema_path = str(schema_path)
    await session.commit()

    return DatasetSchemaResponse(
        table_name=normalized,
        context=context,
        columns=merged_columns,
    )


@router.get("/workspaces/{workspace_id}/schemas", response_model=SchemaListResponse)
async def list_workspace_schemas(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    await _require_workspace_access(session, current_user.id, workspace_id)
    datasets = await DatasetRepository.list_for_workspace(session, workspace_id)
    schemas: list[dict[str, Any]] = []
    for ds in datasets:
        schemas.append(
            {
                "table_name": ds.table_name,
                "schema_path": ds.schema_path,
                "source_path": ds.source_path,
                "updated_at": ds.updated_at,
            }
        )
    return SchemaListResponse(schemas=schemas)


def _format_sse_event(event: str, payload: Any) -> str:
    data = json.dumps(payload, default=str)
    return f"event: {event}\ndata: {data}\n\n"


def _parse_terminal_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=os.name != "nt")
    except Exception:
        return command.split()


def _validate_terminal_cwd(cwd: str | None, workspace_dir: str) -> None:
    if not cwd:
        return
    base = Path(workspace_dir).resolve()
    requested = Path(cwd).expanduser()
    resolved = requested.resolve() if requested.is_absolute() else (base / requested).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="cwd must stay within the workspace directory.",
        ) from exc


def _enforce_terminal_command_policy(command: str, config: Any) -> None:
    trimmed = (command or "").strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Command must not be empty.")

    if _BLOCKED_TERMINAL_SYNTAX_RE.search(trimmed):
        raise HTTPException(
            status_code=400,
            detail="Command contains unsupported shell syntax. Use a single command without chaining/redirection.",
        )

    denylist = list(_DEFAULT_TERMINAL_DENYLIST)
    denylist.extend([p for p in (config.terminal_command_denylist or []) if str(p).strip()])
    for pattern in denylist:
        try:
            if re.search(pattern, trimmed):
                raise HTTPException(status_code=400, detail="Command blocked by terminal security policy.")
        except re.error:
            continue

    allowlist = {
        a.strip().lower()
        for a in (config.terminal_command_allowlist or [])
        if str(a).strip()
    }
    effective_allowlist = allowlist or _DEFAULT_TERMINAL_ALLOWLIST

    segments = [seg.strip() for seg in trimmed.split("|") if seg.strip()]
    for segment in segments:
        tokens = _parse_terminal_tokens(segment)
        if not tokens:
            continue
        first_token = tokens[0].lower()
        if first_token not in effective_allowlist:
            raise HTTPException(
                status_code=400,
                detail=f"Command '{first_token}' is not allowed by terminal policy.",
            )
        if first_token == "cd" and len(tokens) > 2:
            raise HTTPException(
                status_code=400,
                detail="cd accepts at most one path argument.",
            )


def _enforce_terminal_enabled(config: Any) -> None:
    if bool(getattr(config, "terminal_enabled", False)):
        return
    raise HTTPException(
        status_code=403,
        detail="Terminal feature is disabled. Enable [terminal].enable in inquira.toml.",
    )


def _resolve_websocket_user_id(user_id: str) -> str | None:
    if websocket_manager.is_connected(user_id):
        return user_id
    if websocket_manager.is_connected("current_user"):
        return "current_user"
    return None


def _describe_exception(exc: Exception) -> str:
    text = str(exc).strip()
    if text:
        return text
    return exc.__class__.__name__
