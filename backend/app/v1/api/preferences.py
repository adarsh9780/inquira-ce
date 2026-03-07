"""API v1 user preferences and keychain-backed API key routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..schemas.common import MessageResponse
from ..schemas.preferences import (
    ApiKeyUpdateRequest,
    PreferencesResponse,
    PreferencesUpdateRequest,
)
from ..services.secret_storage_service import SecretStorageService
from ...services.llm_provider_catalog import (
    SUPPORTED_LLM_PROVIDERS,
    all_provider_model_catalogs,
    normalize_llm_provider,
    provider_model_catalog,
    provider_requires_api_key,
)
from ...services.execution_config import load_execution_runtime_config
from .deps import ensure_appdata_principal, get_current_user

router = APIRouter(
    prefix="/preferences",
    tags=["V1 Preferences"],
    dependencies=[Depends(ensure_appdata_principal)],
)


def _load_enabled_models(raw_json: str, provider: str) -> list[str]:
    catalog = provider_model_catalog(provider)
    allowed = set(catalog["main_models"])
    parsed: list[str] = []
    try:
        raw = json.loads(str(raw_json or "[]"))
        if isinstance(raw, list):
            parsed = [str(item).strip() for item in raw]
    except Exception:  # noqa: BLE001
        parsed = []

    enabled: list[str] = []
    seen: set[str] = set()
    for model in parsed:
        if model and model in allowed and model not in seen:
            seen.add(model)
            enabled.append(model)
    if enabled:
        return enabled
    return list(catalog["main_models"])


def _to_response(prefs, api_key_presence: dict[str, bool]) -> PreferencesResponse:
    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    catalog = provider_model_catalog(provider)
    enabled_models = _load_enabled_models(getattr(prefs, "enabled_main_models_json", "[]"), provider)
    selected_model = str(getattr(prefs, "selected_model", "") or "").strip()
    if selected_model not in enabled_models:
        selected_model = catalog["default_main_model"]
        if selected_model not in enabled_models:
            selected_model = enabled_models[0] if enabled_models else catalog["default_main_model"]
    selected_lite_model = str(getattr(prefs, "selected_lite_model", "") or "").strip()
    if selected_lite_model not in catalog["lite_models"]:
        selected_lite_model = catalog["default_lite_model"]

    execution_runtime = load_execution_runtime_config()
    requires_api_key = provider_requires_api_key(provider)
    selected_key_present = bool(api_key_presence.get(provider))
    return PreferencesResponse(
        llm_provider=provider,
        available_providers=list(SUPPORTED_LLM_PROVIDERS),
        selected_model=selected_model,
        selected_lite_model=selected_lite_model,
        enabled_models=enabled_models,
        schema_context=prefs.schema_context,
        allow_schema_sample_values=bool(prefs.allow_schema_sample_values),
        chat_overlay_width=float(prefs.chat_overlay_width),
        is_sidebar_collapsed=bool(prefs.is_sidebar_collapsed),
        hide_shortcuts_modal=bool(prefs.hide_shortcuts_modal),
        active_workspace_id=prefs.active_workspace_id,
        active_dataset_path=prefs.active_dataset_path,
        active_table_name=prefs.active_table_name,
        api_key_present=selected_key_present,
        available_models=enabled_models,
        provider_available_main_models=list(catalog["main_models"]),
        provider_available_lite_models=list(catalog["lite_models"]),
        provider_model_catalogs=all_provider_model_catalogs(),
        api_key_present_by_provider=api_key_presence,
        selected_provider_requires_api_key=requires_api_key,
        selected_provider_api_key_present=selected_key_present,
        plotly_theme_mode=execution_runtime.plotly_theme_mode,
    )


@router.get("", response_model=PreferencesResponse)
async def get_preferences(
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    await session.commit()
    key_presence = SecretStorageService.get_api_key_presence_map(
        current_user.id, list(SUPPORTED_LLM_PROVIDERS)
    )
    return _to_response(prefs, key_presence)


@router.put("", response_model=PreferencesResponse)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    catalog = provider_model_catalog(provider)

    if payload.llm_provider is not None:
        provider = normalize_llm_provider(payload.llm_provider)
        prefs.llm_provider = provider
        catalog = provider_model_catalog(provider)

    if payload.enabled_models is not None:
        allowed = set(catalog["main_models"])
        cleaned: list[str] = []
        seen: set[str] = set()
        for model in payload.enabled_models:
            value = str(model or "").strip()
            if not value or value not in allowed or value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        prefs.enabled_main_models_json = json.dumps(cleaned or list(catalog["main_models"]))

    enabled_models = _load_enabled_models(getattr(prefs, "enabled_main_models_json", "[]"), provider)
    if payload.selected_model is not None:
        selected_model = str(payload.selected_model or "").strip()
        if selected_model in enabled_models:
            prefs.selected_model = selected_model
    if payload.selected_lite_model is not None:
        selected_lite_model = str(payload.selected_lite_model or "").strip()
        if selected_lite_model in catalog["lite_models"]:
            prefs.selected_lite_model = selected_lite_model
    if payload.schema_context is not None:
        prefs.schema_context = payload.schema_context
    if payload.allow_schema_sample_values is not None:
        prefs.allow_schema_sample_values = payload.allow_schema_sample_values
    if payload.chat_overlay_width is not None:
        prefs.chat_overlay_width = payload.chat_overlay_width
    if payload.is_sidebar_collapsed is not None:
        prefs.is_sidebar_collapsed = payload.is_sidebar_collapsed
    if payload.hide_shortcuts_modal is not None:
        prefs.hide_shortcuts_modal = payload.hide_shortcuts_modal

    # Allow explicit clear by empty string; keep None as "no change" for workspace id.
    if payload.active_workspace_id is not None:
        prefs.active_workspace_id = payload.active_workspace_id or None
    if payload.active_dataset_path is not None:
        prefs.active_dataset_path = payload.active_dataset_path or None
    if payload.active_table_name is not None:
        prefs.active_table_name = payload.active_table_name or None

    if str(getattr(prefs, "selected_model", "") or "").strip() not in enabled_models:
        prefs.selected_model = (
            enabled_models[0] if enabled_models else provider_model_catalog(provider)["default_main_model"]
        )
    if str(getattr(prefs, "selected_lite_model", "") or "").strip() not in catalog["lite_models"]:
        prefs.selected_lite_model = provider_model_catalog(provider)["default_lite_model"]

    await session.commit()
    key_presence = SecretStorageService.get_api_key_presence_map(
        current_user.id, list(SUPPORTED_LLM_PROVIDERS)
    )
    return _to_response(prefs, key_presence)


@router.put("/api-key", response_model=MessageResponse)
async def set_api_key(
    payload: ApiKeyUpdateRequest,
    current_user=Depends(get_current_user),
):
    provider = normalize_llm_provider(payload.provider)
    api_key = (payload.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    try:
        SecretStorageService.set_api_key(current_user.id, api_key, provider=provider)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to persist API key in OS keychain.") from exc
    return MessageResponse(message=f"API key for provider '{provider}' saved to OS keychain.")


@router.delete("/api-key", response_model=MessageResponse)
async def delete_api_key(
    provider: str | None = None,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    selected_provider = normalize_llm_provider(provider or getattr(prefs, "llm_provider", "openrouter"))
    try:
        SecretStorageService.delete_api_key(current_user.id, provider=selected_provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Failed to remove API key from OS keychain.") from exc
    return MessageResponse(message=f"API key for provider '{selected_provider}' removed from OS keychain.")
