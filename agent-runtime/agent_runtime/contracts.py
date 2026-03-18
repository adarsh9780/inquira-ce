from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    request_id: str
    user_id: str
    workspace_id: str
    conversation_id: str
    question: str
    current_code: str = ""
    model: str = ""
    context: str = ""
    table_name: str = ""
    preferred_table_name: str = ""
    data_path: str = ""
    active_schema: dict[str, Any] = Field(default_factory=dict)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    llm: dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    run_id: str
    result: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    api_major: int
    service: str = "agent-runtime"
