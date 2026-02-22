"""API v1 runtime endpoints for workspace-scoped execution and preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.code_executor import execute_code
from ..db.session import get_db_session
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .deps import get_current_user

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


class SchemaListResponse(BaseModel):
    schemas: list[dict[str, Any]]


def _normalize_table_name(raw: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in raw.strip()).lower()


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
            with schema_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return DatasetSchemaResponse(
                table_name=normalized,
                context=str(data.get("context", "")),
                columns=data.get("columns", []),
            )

    con = duckdb.connect(workspace.duckdb_path)
    try:
        rows = con.execute(f'DESCRIBE "{normalized}"').fetchall()
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
    schema_doc = {
        "table_name": normalized,
        "context": payload.context or "",
        "columns": payload.columns or [],
    }
    with schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema_doc, f, indent=2)

    if dataset is not None:
        dataset.schema_path = str(schema_path)
        await session.commit()

    return DatasetSchemaResponse(
        table_name=normalized,
        context=str(schema_doc.get("context", "")),
        columns=schema_doc["columns"],
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
