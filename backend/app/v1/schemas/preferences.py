"""Pydantic schemas for v1 user preferences endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderModelCatalog(BaseModel):
    main_models: list[str] = Field(default_factory=list)
    lite_models: list[str] = Field(default_factory=list)
    default_main_model: str = ""
    default_lite_model: str = ""


class PreferencesResponse(BaseModel):
    llm_provider: str = "openrouter"
    available_providers: list[str] = Field(default_factory=list)
    selected_model: str = "google/gemini-2.5-flash"
    selected_lite_model: str = "google/gemini-2.5-flash-lite"
    selected_coding_model: str = "google/gemini-2.5-flash"
    enabled_models: list[str] = Field(default_factory=list)
    schema_context: str = ""
    allow_schema_sample_values: bool = False
    terminal_risk_acknowledged: bool = False
    chat_overlay_width: float = 0.25
    is_sidebar_collapsed: bool = True
    hide_shortcuts_modal: bool = False
    active_workspace_id: str | None = None
    active_dataset_path: str | None = None
    active_table_name: str | None = None
    api_key_present: bool = False
    available_models: list[str] = Field(default_factory=list)
    provider_available_main_models: list[str] = Field(default_factory=list)
    provider_available_lite_models: list[str] = Field(default_factory=list)
    provider_model_catalogs: dict[str, ProviderModelCatalog] = Field(default_factory=dict)
    api_key_present_by_provider: dict[str, bool] = Field(default_factory=dict)
    selected_provider_requires_api_key: bool = True
    selected_provider_api_key_present: bool = False
    plotly_theme_mode: str = "soft"


class PreferencesUpdateRequest(BaseModel):
    llm_provider: str | None = None
    selected_model: str | None = None
    selected_lite_model: str | None = None
    selected_coding_model: str | None = None
    enabled_models: list[str] | None = None
    schema_context: str | None = None
    allow_schema_sample_values: bool | None = None
    terminal_risk_acknowledged: bool | None = None
    chat_overlay_width: float | None = Field(default=None, ge=0.1, le=0.9)
    is_sidebar_collapsed: bool | None = None
    hide_shortcuts_modal: bool | None = None
    active_workspace_id: str | None = None
    active_dataset_path: str | None = None
    active_table_name: str | None = None


class ApiKeyUpdateRequest(BaseModel):
    provider: str = "openrouter"
    api_key: str = Field(min_length=1)
