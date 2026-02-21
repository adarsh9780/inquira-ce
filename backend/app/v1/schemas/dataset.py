"""Pydantic schemas for workspace dataset endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetAddRequest(BaseModel):
    """Add dataset payload using a local source file path."""

    source_path: str = Field(min_length=1)


class DatasetResponse(BaseModel):
    """Workspace dataset response."""

    id: int
    workspace_id: str
    source_path: str
    table_name: str
    row_count: int | None
    file_type: str | None
    created_at: datetime
    updated_at: datetime


class DatasetListResponse(BaseModel):
    """List datasets response."""

    datasets: list[DatasetResponse]
