"""API v1 authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db_session
from ..schemas.auth import AuthUserResponse, LoginRequest, RegisterRequest
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["V1 Authentication"])


@router.post("/register", response_model=AuthUserResponse)
async def register_user(
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
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
        secure=False,
    )
    return AuthUserResponse(user_id=user_id, username=payload.username, plan=plan)


@router.post("/login", response_model=AuthUserResponse)
async def login_user(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
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
        secure=False,
    )
    return AuthUserResponse(user_id=user_id, username=payload.username, plan=plan)
