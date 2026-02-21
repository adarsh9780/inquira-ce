"""Pydantic schemas for workspace APIs."""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation payload."""

    name: str = Field(min_length=1, max_length=120)


class WorkspaceResponse(BaseModel):
    """Workspace response payload."""

    id: str
    name: str
    is_active: bool
    duckdb_path: str
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(BaseModel):
    """List workspaces response."""

    workspaces: list[WorkspaceResponse]
