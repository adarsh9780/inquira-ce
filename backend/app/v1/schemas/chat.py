"""Schemas for v1 chat analysis endpoint."""

from pydantic import BaseModel, Field


class ChatImageAttachment(BaseModel):
    """Inline image attachment payload."""

    attachment_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    data_base64: str = Field(min_length=1)


class AnalyzeRequest(BaseModel):
    """Analyze input payload bound to workspace+conversation."""

    workspace_id: str
    conversation_id: str | None = None
    question: str = Field(min_length=1)
    current_code: str = ""
    model: str = "google/gemini-2.5-flash"
    context: str | None = None
    use_selected_turn_context: bool = False
    selected_parent_turn_id: str | None = None
    table_name: str | None = None
    preferred_table_name: str | None = None
    active_schema: dict | None = None
    attachments: list[ChatImageAttachment] = Field(default_factory=list)
    api_key: str | None = None


class AnalyzeResponse(BaseModel):
    """Analyze output payload with persistence references."""

    conversation_id: str
    turn_id: str
    is_safe: bool
    is_relevant: bool
    code: str
    explanation: str
    result_explanation: str | None = None
    code_explanation: str | None = None
    run_id: str | None = None
    execution: dict | None = None
    metadata: dict | None = None
    artifacts: list[dict] = Field(default_factory=list)
    final_script_artifact_id: str | None = None


class InterventionResponseRequest(BaseModel):
    """User decision payload for a pending agent intervention."""

    selected: list[str] = Field(default_factory=list)


class InterventionResponseAck(BaseModel):
    """Ack payload for intervention response submissions."""

    intervention_id: str
    accepted: bool
