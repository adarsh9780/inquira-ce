"""Pydantic schemas for v1 user preferences endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PreferencesResponse(BaseModel):
    selected_model: str = "google/gemini-2.5-flash"
    schema_context: str = ""
    allow_schema_sample_values: bool = False
    chat_overlay_width: float = 0.25
    is_sidebar_collapsed: bool = True
    hide_shortcuts_modal: bool = False
    active_workspace_id: str | None = None
    active_dataset_path: str | None = None
    active_table_name: str | None = None
    api_key_present: bool = False
    available_models: list[str] = Field(default_factory=list)


class PreferencesUpdateRequest(BaseModel):
    selected_model: str | None = None
    schema_context: str | None = None
    allow_schema_sample_values: bool | None = None
    chat_overlay_width: float | None = Field(default=None, ge=0.1, le=0.9)
    is_sidebar_collapsed: bool | None = None
    hide_shortcuts_modal: bool | None = None
    active_workspace_id: str | None = None
    active_dataset_path: str | None = None
    active_table_name: str | None = None


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(min_length=1)
