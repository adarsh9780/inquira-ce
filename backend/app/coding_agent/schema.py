"""Schemas for the reusable coding subagent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisOutput(BaseModel):
    code: str | None = None
    explanation: str | None = None
    output_contract: list[dict[str, str]] = Field(default_factory=list)
    search_schema_queries: list[str] = Field(default_factory=list)
    selected_tables: list[str] = Field(default_factory=list)
    join_keys: list[str] = Field(default_factory=list)
    joins_used: bool = False
