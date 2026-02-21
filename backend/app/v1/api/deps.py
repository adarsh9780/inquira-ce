"""Shared API dependencies for v1 endpoints."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..services.auth_service import AuthService


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Resolve authenticated user from HTTP-only session cookie."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await AuthService.resolve_user_from_session(session, session_token)


def get_langgraph_manager(request: Request):
    """Return shared workspace LangGraph manager from app state."""
    manager = getattr(request.app.state, "workspace_langgraph_manager", None)
    if manager is None:
        raise HTTPException(status_code=500, detail="Workspace LangGraph manager not initialized")
    return manager


def get_workspace_deletion_service(request: Request):
    """Return shared workspace deletion service from app state."""
    service = getattr(request.app.state, "workspace_deletion_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="Workspace deletion service not initialized")
    return service
