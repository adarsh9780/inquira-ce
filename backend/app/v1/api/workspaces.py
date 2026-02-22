"""API v1 workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceDeletionJobListResponse,
    WorkspaceDeletionJobResponse,
    WorkspaceListResponse,
    WorkspaceResponse,
)
from ..services.workspace_deletion_service import WorkspaceDeletionService
from ..services.workspace_service import WorkspaceService
from .deps import get_current_user, get_langgraph_manager, get_workspace_deletion_service

router = APIRouter(prefix="/workspaces", tags=["V1 Workspaces"])


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """List all workspaces for the authenticated user."""
    workspaces = await WorkspaceService.list_user_workspaces(session, current_user.id)
    return WorkspaceListResponse(
        workspaces=[
            WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                is_active=bool(ws.is_active),
                duckdb_path=ws.duckdb_path,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
            )
            for ws in workspaces
        ]
    )


@router.post("", response_model=WorkspaceResponse)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Create a workspace for the authenticated user."""
    ws = await WorkspaceService.create_workspace(session, current_user, payload.name)
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        is_active=bool(ws.is_active),
        duckdb_path=ws.duckdb_path,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.put("/{workspace_id}/activate", response_model=WorkspaceResponse)
async def activate_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Set the active workspace for the authenticated user."""
    ws = await WorkspaceService.activate_workspace(session, current_user.id, workspace_id)
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        is_active=bool(ws.is_active),
        duckdb_path=ws.duckdb_path,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.delete(
    "/{workspace_id}",
    response_model=WorkspaceDeletionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delete_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    langgraph_manager=Depends(get_langgraph_manager),
    workspace_deletion_service: WorkspaceDeletionService = Depends(get_workspace_deletion_service),
):
    """Queue async workspace deletion and return job id for polling."""
    job = await workspace_deletion_service.enqueue_workspace_deletion(
        session=session,
        user=current_user,
        workspace_id=workspace_id,
        langgraph_manager=langgraph_manager,
    )
    return WorkspaceDeletionJobResponse(
        job_id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/deletions", response_model=WorkspaceDeletionJobListResponse)
async def list_workspace_deletions(
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    workspace_deletion_service: WorkspaceDeletionService = Depends(get_workspace_deletion_service),
):
    """List active workspace deletion jobs for the current user."""
    jobs = await workspace_deletion_service.list_active_jobs_for_user(session, current_user.id)
    return WorkspaceDeletionJobListResponse(
        jobs=[
            WorkspaceDeletionJobResponse(
                job_id=job.id,
                workspace_id=job.workspace_id,
                status=job.status,
                error_message=job.error_message,
                created_at=job.created_at,
                updated_at=job.updated_at,
            )
            for job in jobs
        ]
    )


@router.get("/deletions/{job_id}", response_model=WorkspaceDeletionJobResponse)
async def get_workspace_deletion(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
    workspace_deletion_service: WorkspaceDeletionService = Depends(get_workspace_deletion_service),
):
    """Get one workspace deletion job status by id."""
    job = await workspace_deletion_service.get_job_for_user(session, current_user.id, job_id)
    return WorkspaceDeletionJobResponse(
        job_id=job.id,
        workspace_id=job.workspace_id,
        status=job.status,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
