"""API v1 runtime endpoints for workspace-scoped execution and preview."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.code_executor import execute_code
from ..db.session import get_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_repository import WorkspaceRepository
from ..services.secret_storage_service import SecretStorageService
from .deps import get_current_user
from ...core.prompt_library import get_prompt
from ...services.llm_service import LLMService
from ...services.llm_runtime_config import load_llm_runtime_config

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


def _normalize_table_name(raw: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()


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
    working_dir = str(Path(workspace.duckdb_path).parent)

    bootstrap = (
        "import duckdb\n"
        f"conn = duckdb.connect(r'''{workspace.duckdb_path}''')\n"
    )
    result = await execute_code(
        code=f"{bootstrap}\n{payload.code}",
        timeout=payload.timeout,
        working_dir=working_dir,
    )
    return ExecuteResponse(**result)


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
    schema_response = await asyncio.to_thread(
        llm_service.ask,
        prompt,
        SchemaDescriptionList,
        runtime.schema_max_tokens,
    )
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
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema_doc, f, indent=2)

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
