"""API v1 auth/session routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.auth import AuthConfigResponse, AuthProfileResponse
from ..schemas.common import MessageResponse
from ..services.supabase_auth_service import SupabaseAuthService
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["V1 Auth"])


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config():
    config = SupabaseAuthService.public_auth_config()
    return AuthConfigResponse(
        configured=config.configured,
        auth_provider=config.auth_provider,
        supabase_url=config.supabase_url,
        publishable_key=config.publishable_key,
        site_url=config.site_url,
        manage_account_url=config.manage_account_url,
    )


@router.get("/me", response_model=AuthProfileResponse)
async def get_current_user_profile(current_user=Depends(get_current_user)):
    return AuthProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=getattr(current_user, "email", "") or "",
        plan=str(current_user.plan),
        is_authenticated=bool(getattr(current_user, "is_authenticated", False)),
        is_guest=bool(getattr(current_user, "is_guest", False)),
        auth_provider=str(getattr(current_user, "auth_provider", "local") or "local"),
        manage_account_url=SupabaseAuthService.manage_account_url(),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout_user():
    return MessageResponse(message="Session cleared locally.")
