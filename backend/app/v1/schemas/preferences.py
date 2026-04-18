"""Pydantic schemas for v1 user preferences endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderModelEntry(BaseModel):
    id: str = ""
    display_name: str = ""
    provider: str = "openrouter"
    context_window: int = 0
    recommended_for: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ProviderModelCatalog(BaseModel):
    main_models: list[str] = Field(default_factory=list)
    lite_models: list[str] = Field(default_factory=list)
    default_main_model: str = ""
    default_lite_model: str = ""
    base_url: str = ""
    source: str = "default"
    account_models_configured: bool | None = None
    account_models_url: str = ""
    models: list[ProviderModelEntry] = Field(default_factory=list)


class PreferencesResponse(BaseModel):
    llm_provider: str = "openrouter"
    available_providers: list[str] = Field(default_factory=list)
    selected_model: str = "google/gemini-2.5-flash"
    selected_lite_model: str = "google/gemini-2.5-flash-lite"
    selected_coding_model: str = "google/gemini-2.5-flash"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_top_p: float = 1.0
    llm_top_k: int = 0
    llm_frequency_penalty: float = 0.0
    llm_presence_penalty: float = 0.0
    slow_request_warning_seconds: int = 30
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
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=None, ge=1, le=131072)
    llm_top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    llm_top_k: int | None = Field(default=None, ge=0, le=500)
    llm_frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    llm_presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    slow_request_warning_seconds: int | None = Field(default=None, ge=5, le=600)
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
    api_key: str | None = None
    base_url: str | None = None
    selected_model: str | None = None
    selected_lite_model: str | None = None
    selected_coding_model: str | None = None
    enabled_models: list[str] | None = None
    llm_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    llm_max_tokens: int | None = Field(default=None, ge=1, le=131072)
    llm_top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    llm_top_k: int | None = Field(default=None, ge=0, le=500)
    llm_frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    llm_presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    slow_request_warning_seconds: int | None = Field(default=None, ge=5, le=600)


class ProviderModelsRefreshRequest(BaseModel):
    provider: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class ProviderModelsRefreshResponse(PreferencesResponse):
    detail: str = ""
    error: str = ""


class ApiKeyVerifyRequest(BaseModel):
    provider: str = "openrouter"
    api_key: str = Field(min_length=1)


class ApiKeyVerifyResponse(BaseModel):
    valid: bool
    error: str = ""
