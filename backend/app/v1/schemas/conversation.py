"""Pydantic schemas for conversation and turn APIs."""

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


class FinalTurnRerunResponse(BaseModel):
    """Response for rerunning the selected final turn."""

    conversation_id: str
    turn_id: str
    execution: dict | None
    artifacts: list[dict]
