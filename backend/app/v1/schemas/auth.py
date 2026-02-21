"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Register payload."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    """Login payload."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class AuthUserResponse(BaseModel):
    """Authenticated user metadata returned to frontend."""

    user_id: str
    username: str
    plan: str
