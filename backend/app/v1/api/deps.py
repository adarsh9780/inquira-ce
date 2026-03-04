"""Shared API dependencies for v1 endpoints."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session, get_auth_db_session
from ..repositories.principal_repository import PrincipalRepository
from ..services.auth_service import AuthService


async def get_current_user(
    request: Request,
    auth_session: AsyncSession = Depends(get_auth_db_session),
):
    """Resolve authenticated user from HTTP-only session cookie."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await AuthService.resolve_user_from_session(auth_session, session_token)


async def ensure_appdata_principal(
    appdata_session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Ensure authenticated user identity exists in appdata principal table."""
    plan = getattr(current_user, "plan", "FREE")
    plan_value = plan.value if hasattr(plan, "value") else str(plan)
    username = str(getattr(current_user, "username", current_user.id))
    principal = await PrincipalRepository.get_or_create(
        session=appdata_session,
        principal_id=current_user.id,
        username=username,
        plan=plan_value,
    )
    if appdata_session.new or appdata_session.dirty:
        await appdata_session.commit()
    return principal


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
