"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel


class AuthUserResponse(BaseModel):
    """Authenticated user metadata returned to frontend."""

    user_id: str
    username: str
    plan: str
