"""API v1 authentication routes."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_auth_db_session
from ..schemas.common import MessageResponse
from ..schemas.auth import AuthUserResponse, LoginRequest, RegisterRequest
from ..services.auth_service import AuthService
from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["V1 Authentication"])


def _should_use_secure_cookie(request: Request) -> bool:
    """Use secure cookies outside explicit local/test hosts."""
    override = os.getenv("INQUIRA_COOKIE_SECURE")
    if override is not None:
        normalized = override.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    host = (request.url.hostname or "").strip().lower()
    if host in {"localhost", "127.0.0.1", "testserver"}:
        return False
    return True


@router.post("/register", response_model=AuthUserResponse)
async def register_user(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_auth_db_session),
):
    """Register a new user and immediately issue login session cookie."""
    session_token, user_id, plan = await AuthService.register_and_login(
        session=session,
        username=payload.username,
        password=payload.password,
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
    )
    return AuthUserResponse(user_id=user_id, username=payload.username, plan=plan)


@router.post("/login", response_model=AuthUserResponse)
async def login_user(
    request: Request,
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_auth_db_session),
):
    """Login user and issue session cookie."""
    session_token, user_id, plan = await AuthService.login(
        session=session,
        username=payload.username,
        password=payload.password,
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=_should_use_secure_cookie(request),
    )
    return AuthUserResponse(user_id=user_id, username=payload.username, plan=plan)


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
async def logout_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_auth_db_session),
):
    """Logout user by deleting current v1 session token and clearing cookie."""
    session_token = request.cookies.get("session_token")
    if session_token:
        await AuthService.logout(session, session_token)
    response.delete_cookie(
        "session_token",
        samesite="lax",
        secure=_should_use_secure_cookie(request),
    )
    return MessageResponse(message="Logout successful")
