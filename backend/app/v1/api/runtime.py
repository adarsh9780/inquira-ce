"""API v1 runtime endpoints for workspace-scoped execution and preview."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.code_executor import (
    execute_code,
    get_workspace_dataframe_rows,
    get_workspace_kernel_status,
    reset_workspace_kernel,
)
from ..db.session import get_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_repository import WorkspaceRepository
from ..services.secret_storage_service import SecretStorageService
from .deps import get_current_user
from ...core.prompt_library import get_prompt
from ...services.llm_service import LLMService
from ...services.llm_runtime_config import load_llm_runtime_config
from ...services.execution_config import load_execution_runtime_config
from ...services.runner_env import install_runner_package

router = APIRouter(tags=["V1 Runtime"])


class ExecuteRequest(BaseModel):
    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(60, ge=1, le=300, description="Max execution time in seconds")


class ExecuteResponse(BaseModel):
    success: bool
    stdout: str = ""
    stderr: str = ""
    error: str | None = None
    result: object | None = None
    result_type: str | None = None
    variables: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {"dataframes": {}, "figures": {}, "scalars": {}}
    )


class DataframeArtifactRowsResponse(BaseModel):
    artifact_id: str
    name: str
    row_count: int
    columns: list[str]
    rows: list[dict[str, Any]]
    offset: int
    limit: int


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


class DatasetSchemaResponse(BaseModel):
    table_name: str
    context: str = ""
    columns: list[dict[str, Any]]


class DatasetPreviewResponse(BaseModel):
    table_name: str
    sample_type: str
    row_count: int
    data: list[dict[str, Any]]


class SaveSchemaRequest(BaseModel):
    context: str = ""
    columns: list[dict[str, Any]]


class RegenerateSchemaRequest(BaseModel):
    context: str | None = None
    model: str | None = None


class SchemaDescriptionItem(BaseModel):
    name: str
    description: str


class SchemaDescriptionList(BaseModel):
    schemas: list[SchemaDescriptionItem]


class SchemaListResponse(BaseModel):
    schemas: list[dict[str, Any]]


_PACKAGE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PACKAGE_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")
_INSTALL_BLOCK_RE = re.compile(
    r"(?im)(?:^\s*!?\s*%?\s*pip\s+install\b|uv\s+pip\s+install\b|python\s+-m\s+pip\s+install\b)"
)


def _normalize_table_name(raw: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()


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
    con = duckdb.connect(duckdb_path)
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


def _read_table_columns_for_prompt(
    duckdb_path: str,
    table_name: str,
    allow_sample_values: bool,
) -> list[dict[str, Any]]:
    con = duckdb.connect(duckdb_path)
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


@router.get("/workspaces/{workspace_id}/paths", response_model=WorkspacePathsResponse)
async def get_workspace_paths(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    workspace_path = Path(workspace.duckdb_path).parent
    return WorkspacePathsResponse(
        workspace_id=workspace_id,
        workspace_dir=str(workspace_path),
        duckdb_path=str(workspace.duckdb_path),
    )


@router.post("/workspaces/{workspace_id}/execute", response_model=ExecuteResponse)
async def execute_workspace_code(
    workspace_id: str,
    payload: ExecuteRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    workspace = await _require_workspace_access(session, current_user.id, workspace_id)
    if _INSTALL_BLOCK_RE.search(payload.code or ""):
        raise HTTPException(
            status_code=400,
            detail=(
                "Package installation commands are blocked in analysis execution. "
                "Use Settings > Runner Packages to install pinned dependencies."
            ),
        )
    result = await execute_code(
        code=payload.code,
        timeout=payload.timeout,
        working_dir=str(Path(workspace.duckdb_path).parent),
        workspace_id=workspace_id,
        workspace_duckdb_path=str(workspace.duckdb_path),
    )
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
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    await _require_workspace_access(session, current_user.id, workspace_id)
    rows = await get_workspace_dataframe_rows(
        workspace_id=workspace_id,
        artifact_id=artifact_id,
        offset=offset,
        limit=limit,
    )
    if rows is None:
        raise HTTPException(status_code=404, detail="Dataframe artifact not found")
    return DataframeArtifactRowsResponse(**rows)


@router.post("/runtime/runner/packages/install", response_model=RunnerPackageInstallResponse)
async def install_runner_runtime_package(
    payload: RunnerPackageInstallRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    await _require_workspace_access(session, current_user.id, payload.workspace_id)
    runtime = load_execution_runtime_config()
    package_spec, index_url = _validate_runner_install_request(payload, runtime)

    try:
        install_result = await asyncio.to_thread(
            install_runner_package,
            runtime,
            package_spec,
            index_url,
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


@router.get(
    "/workspaces/{workspace_id}/kernel/status",
    response_model=KernelStatusResponse,
)
async def get_workspace_kernel_runtime_status(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Return current workspace kernel status."""
    await _require_workspace_access(session, current_user.id, workspace_id)
    status = await get_workspace_kernel_status(workspace_id)
    return KernelStatusResponse(workspace_id=workspace_id, status=status)


@router.post(
    "/workspaces/{workspace_id}/kernel/reset",
    response_model=KernelResetResponse,
)
async def reset_workspace_kernel_runtime(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Reset workspace kernel and clear in-memory execution context."""
    await _require_workspace_access(session, current_user.id, workspace_id)
    reset = await reset_workspace_kernel(workspace_id)
    return KernelResetResponse(workspace_id=workspace_id, reset=reset)


@router.get(
    "/workspaces/{workspace_id}/datasets/{table_name}/schema",
    response_model=DatasetSchemaResponse,
)
async def get_workspace_dataset_schema(
    workspace_id: str,
    table_name: str,
    session: AsyncSession = Depends(get_db_session),
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

    con = duckdb.connect(workspace.duckdb_path)
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
    session: AsyncSession = Depends(get_db_session),
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
    session: AsyncSession = Depends(get_db_session),
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
    generated_by_name = {str(item.name): str(item.description) for item in generated_items}

    merged_columns = [
        {
            "name": col["name"],
            "dtype": col["dtype"],
            "description": generated_by_name.get(col["name"], ""),
            "samples": col.get("samples", []),
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


@router.get(
    "/workspaces/{workspace_id}/datasets/{table_name}/preview",
    response_model=DatasetPreviewResponse,
)
async def get_workspace_dataset_preview(
    workspace_id: str,
    table_name: str,
    sample_type: str = Query(default="random", pattern="^(random|first)$"),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
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

    con = duckdb.connect(workspace.duckdb_path)
    try:
        if sample_type == "first":
            query = f'SELECT * FROM "{normalized}" LIMIT {limit}'
        else:
            query = f'SELECT * FROM "{normalized}" USING SAMPLE {limit} ROWS'
        df = con.execute(query).fetchdf()
    finally:
        con.close()

    data = df.to_dict(orient="records")
    return DatasetPreviewResponse(
        table_name=normalized,
        sample_type=sample_type,
        row_count=len(data),
        data=data,
    )


@router.get("/workspaces/{workspace_id}/schemas", response_model=SchemaListResponse)
async def list_workspace_schemas(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
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
