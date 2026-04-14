"""Shared API dependencies for v1 endpoints."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..models.enums import UserPlan
from ..repositories.principal_repository import PrincipalRepository
from ..services.supabase_auth_service import SupabaseAuthService


async def get_current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    """Resolve the effective current user, falling back to guest mode."""
    return await SupabaseAuthService.resolve_current_user(authorization)


async def ensure_appdata_principal(
    appdata_session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    """Ensure effective user identity exists in appdata principal table."""
    plan = getattr(current_user, "plan", UserPlan.FREE.value)
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



def require_minimum_plan(required_plan: UserPlan | str) -> Callable:
    async def _dependency(current_user=Depends(get_current_user)):
        current_plan = getattr(current_user, "plan", UserPlan.FREE.value)
        if not SupabaseAuthService.has_minimum_plan(current_plan, required_plan):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires the {str(required_plan)} plan.",
            )
        return current_user

    return _dependency



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


def get_dataset_deletion_service(request: Request):
    """Return shared dataset deletion service from app state."""
    service = getattr(request.app.state, "dataset_deletion_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="Dataset deletion service not initialized")
    return service
