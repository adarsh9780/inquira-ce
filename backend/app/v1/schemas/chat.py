"""Schemas for v1 chat analysis endpoint."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Analyze input payload bound to workspace+conversation."""

    workspace_id: str
    conversation_id: str | None = None
    question: str = Field(min_length=1)
    current_code: str = ""
    model: str = "gemini-2.5-flash"
    context: str | None = None


class AnalyzeResponse(BaseModel):
    """Analyze output payload with persistence references."""

    conversation_id: str
    turn_id: str
    is_safe: bool
    is_relevant: bool
    code: str
    explanation: str
