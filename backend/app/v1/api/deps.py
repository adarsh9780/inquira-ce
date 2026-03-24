"""Shared API dependencies for v1 endpoints."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..repositories.principal_repository import PrincipalRepository
from ..services.auth_service import AuthService
from ...core.logger import logprint


async def get_current_user(request: Request):
    """Resolve authenticated user from a Supabase bearer token, or return anonymous user."""
    auth_header = str(request.headers.get("authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        # When no login is provided, we default to the 'Guest' principal
        return AuthService.get_anonymous_user()

    access_token = auth_header.split(" ", 1)[1].strip()
    try:
        return await AuthService.resolve_supabase_user(access_token)
    except HTTPException as exc:
        # If the token is invalid/expired in a local context, we could fallback to Guest
        # instead of hard-rejecting, to minimize friction.
        if exc.status_code == 401:
            logprint(
                "[AUTH] Invalid token provided, falling back to Guest session.",
                level="INFO",
            )
            return AuthService.get_anonymous_user()
        raise exc


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
