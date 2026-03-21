"""API v1 authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.common import MessageResponse
from ..schemas.auth import AuthUserResponse
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["V1 Authentication"])


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user_profile(current_user=Depends(get_current_user)):
    """Return authenticated user profile and plan for UI rendering."""
    plan = getattr(current_user, "plan", "FREE")
    plan_value = plan.value if hasattr(plan, "value") else str(plan)
    return AuthUserResponse(
        user_id=current_user.id,
        username=current_user.username,
        plan=plan_value,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout_user():
    """Return success after the client clears its Supabase session locally."""
    return MessageResponse(message="Logout successful")
