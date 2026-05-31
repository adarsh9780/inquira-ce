"""Pydantic schemas for conversation and turn APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    """Conversation create payload."""

    title: str | None = Field(default=None, max_length=255)


class ConversationUpdateRequest(BaseModel):
    """Conversation update payload."""

    title: str | None = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    """Conversation response."""

    id: str
    workspace_id: str
    title: str
    last_turn_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Conversation list response."""

    conversations: list[ConversationResponse]


class TurnResponse(BaseModel):
    """Turn response entry."""

    id: str
    parent_turn_id: str | None = None
    result_kind: str | None = None
    code_path: str | None = None
    manifest_path: str | None = None
    seq_no: int
    sibling_order: int = 0
    user_text: str
    assistant_text: str
    tool_events: list[dict] | None
    metadata: dict | None
    code_snapshot: str | None
    created_at: datetime


class TurnPageResponse(BaseModel):
    """Paginated turn response."""

    turns: list[TurnResponse]
    next_cursor: str | None


class TurnRelationsResponse(BaseModel):
    """Turn lineage and navigation payload."""

    current: TurnResponse
    parent: TurnResponse | None
    children: list[TurnResponse]
    previous_turn: TurnResponse | None
    next_turn: TurnResponse | None


class TurnArtifactSummary(BaseModel):
    """Turn-owned artifact summary."""

    artifact_id: str
    logical_name: str
    display_name: str | None = None
    kind: str
    row_count: int | None = None
    columns: list[dict] | None = None
    created_at: str
    status: str


class TurnArtifactListResponse(BaseModel):
    """Turn-owned artifact list response."""

    artifacts: list[TurnArtifactSummary]
    total: int


class TurnArtifactMetadataResponse(BaseModel):
    """Turn-owned artifact metadata response."""

    artifact_id: str
    run_id: str
    workspace_id: str
    logical_name: str
    display_name: str | None = None
    kind: str
    pointer: str
    table_name: str | None = None
    schema_columns: list[dict] | None = Field(default=None, alias="schema")
    row_count: int | None = None
    payload: dict | None = None
    created_at: str
    expires_at: str
    status: str
    error: str | None = None


class TurnDataframeArtifactRowsResponse(BaseModel):
    """Rows for one turn-owned dataframe artifact."""

    artifact_id: str
    name: str
    display_name: str | None = None
    row_count: int
    columns: list[str]
    rows: list[dict]
    offset: int
    limit: int


class TurnArtifactDeleteResponse(BaseModel):
    """Turn artifact deletion response."""

    artifact_id: str
    deleted: bool


class TurnTreeNodeResponse(BaseModel):
    """Recursive turn tree node."""

    id: str
    parent_turn_id: str | None = None
    seq_no: int
    sibling_order: int = 0
    user_text: str
    assistant_text: str
    created_at: datetime
    children: list[TurnTreeNodeResponse] = Field(default_factory=list)


class TurnTreeResponse(BaseModel):
    """Complete conversation turn tree."""

    roots: list[TurnTreeNodeResponse]
    current_turn_id: str | None = None
    final_turn_id: str | None = None


class TurnParentUpdateRequest(BaseModel):
    """Move one turn under another visible turn in the same conversation."""

    parent_turn_id: str


class TurnOrderUpdateRequest(BaseModel):
    """Replace display order for all visible siblings under one parent."""

    parent_turn_id: str | None = None
    turn_ids: list[str] = Field(min_length=1)


class GlobalTurnTreeConversationResponse(BaseModel):
    """Workspace-level tree group for one conversation."""

    id: str
    title: str
    last_turn_at: datetime | None
    created_at: datetime
    updated_at: datetime
    final_turn_id: str | None = None
    roots: list[TurnTreeNodeResponse] = Field(default_factory=list)


class GlobalTurnTreeResponse(BaseModel):
    """All visible conversation trees for a workspace."""

    conversations: list[GlobalTurnTreeConversationResponse]


class FinalTurnRerunResponse(BaseModel):
    """Response for rerunning the selected final turn."""

    conversation_id: str
    turn_id: str
    execution: dict | None
    artifacts: list[dict]
