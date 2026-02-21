"""API v1 workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..schemas.common import MessageResponse
from ..schemas.workspace import WorkspaceCreateRequest, WorkspaceListResponse, WorkspaceResponse
from ..services.workspace_service import WorkspaceService
from .deps import get_current_user

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


@router.delete("/{workspace_id}", response_model=MessageResponse)
async def delete_workspace(
    workspace_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    """Hard delete workspace and all owned resources."""
    await WorkspaceService.delete_workspace(session, current_user, workspace_id)
    return MessageResponse(message="Workspace deleted")
