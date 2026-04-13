"""API v1 workspace dataset routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..schemas.dataset import (
    BrowserDatasetSyncRequest,
    DatasetAddRequest,
    DatasetDeleteResponse,
    DatasetListResponse,
    DatasetResponse,
)
from ..services.dataset_service import DatasetService
from .deps import ensure_appdata_principal, get_current_user

router = APIRouter(
    tags=["V1 Datasets"],
    dependencies=[Depends(ensure_appdata_principal)],
)


@router.get("/workspaces/{workspace_id}/datasets", response_model=DatasetListResponse)
async def list_workspace_datasets(
    workspace_id: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """List datasets inside one workspace."""
    datasets = await DatasetService.list_datasets(session, current_user.id, workspace_id)
    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                id=ds.id,
                workspace_id=ds.workspace_id,
                source_path=ds.source_path,
                table_name=ds.table_name,
                row_count=ds.row_count,
                file_type=ds.file_type,
                created_at=ds.created_at,
                updated_at=ds.updated_at,
            )
            for ds in datasets
        ]
    )


@router.post("/workspaces/{workspace_id}/datasets", response_model=DatasetResponse)
async def add_workspace_dataset(
    workspace_id: str,
    payload: DatasetAddRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Add or refresh a dataset in the workspace DuckDB."""
    ds = await DatasetService.add_dataset(session, current_user, workspace_id, payload.source_path)
    return DatasetResponse(
        id=ds.id,
        workspace_id=ds.workspace_id,
        source_path=ds.source_path,
        table_name=ds.table_name,
        row_count=ds.row_count,
        file_type=ds.file_type,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.post("/workspaces/{workspace_id}/datasets/browser-sync", response_model=DatasetResponse)
async def sync_browser_workspace_dataset(
    workspace_id: str,
    payload: BrowserDatasetSyncRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Sync browser-loaded table into workspace dataset catalog/schema metadata."""
    ds = await DatasetService.sync_browser_dataset(
        session=session,
        user=current_user,
        workspace_id=workspace_id,
        table_name=payload.table_name,
        columns=payload.columns,
        row_count=payload.row_count,
        allow_sample_values=payload.allow_sample_values,
    )
    return DatasetResponse(
        id=ds.id,
        workspace_id=ds.workspace_id,
        source_path=ds.source_path,
        table_name=ds.table_name,
        row_count=ds.row_count,
        file_type=ds.file_type,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


@router.delete("/workspaces/{workspace_id}/datasets/{table_name}", response_model=DatasetDeleteResponse)
async def remove_workspace_dataset(
    workspace_id: str,
    table_name: str,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Remove one dataset from workspace catalog metadata."""
    removed = await DatasetService.remove_dataset(
        session=session,
        principal_id=current_user.id,
        workspace_id=workspace_id,
        table_name=table_name,
    )
    return DatasetDeleteResponse(
        workspace_id=removed.workspace_id,
        table_name=removed.table_name,
        removed=True,
    )
