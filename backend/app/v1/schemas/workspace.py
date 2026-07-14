"""Pydantic schemas for workspace APIs."""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation payload."""

    name: str = Field(min_length=1, max_length=120)
    schema_context: str = ""


class WorkspaceRenameRequest(BaseModel):
    """Workspace rename payload."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    schema_context: str | None = None


class WorkspaceResponse(BaseModel):
    """Workspace response payload."""

    id: str
    name: str
    is_active: bool
    duckdb_path: str
    schema_context: str = ""
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(BaseModel):
    """List workspaces response."""

    workspaces: list[WorkspaceResponse]


class WorkspaceSummaryResponse(BaseModel):
    """On-demand workspace summary payload for lightweight UI details."""

    id: str
    name: str
    is_active: bool
    schema_context: str = ""
    created_at: datetime
    updated_at: datetime
    table_count: int
    table_names: list[str]
    conversation_count: int


class WorkspaceAIConfigUpdateRequest(BaseModel):
    """Editable workspace AI overrides. API credentials remain application scoped."""

    llm_provider_override: str | None = Field(default=None, max_length=32)
    main_model_override: str | None = Field(default=None, max_length=120)
    lite_model_override: str | None = Field(default=None, max_length=120)
    llm_temperature_override: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_max_tokens_override: int | None = Field(default=None, ge=1, le=131072)
    llm_top_p_override: float | None = Field(default=None, ge=0.0, le=1.0)
    allow_llm_data_samples: bool


class WorkspaceAIConfigResponse(BaseModel):
    """Global defaults, explicit overrides, resolved values, and readiness."""

    workspace_id: str
    defaults: dict
    overrides: dict
    effective: dict
    readiness: dict


class WorkspaceDeletionJobResponse(BaseModel):
    """Workspace deletion job status payload."""

    job_id: str
    workspace_id: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceDeletionJobListResponse(BaseModel):
    """List active deletion jobs response."""

    jobs: list[WorkspaceDeletionJobResponse]


class WorkspaceDatabaseClearResponse(BaseModel):
    """Workspace database clear payload."""

    workspace_id: str
    cleared: bool
    detail: str
