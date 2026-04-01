"""Auth/session schemas for CE desktop flows."""

from __future__ import annotations

from pydantic import BaseModel

from .common import MessageResponse


class AuthConfigResponse(BaseModel):
    configured: bool
    auth_provider: str
    supabase_url: str = ""
    publishable_key: str = ""
    site_url: str = ""
    manage_account_url: str = ""


class AuthProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str = ""
    plan: str
    is_authenticated: bool
    is_guest: bool
    auth_provider: str
    manage_account_url: str = ""


__all__ = [
    "AuthConfigResponse",
    "AuthProfileResponse",
    "MessageResponse",
]
