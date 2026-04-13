"""API v1 user preferences and keychain-backed API key routes."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_appdata_db_session
from ..repositories.preferences_repository import PreferencesRepository
from ..schemas.common import MessageResponse
from ..schemas.preferences import (
    ApiKeyVerifyRequest,
    ApiKeyVerifyResponse,
    ApiKeyUpdateRequest,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ProviderModelCatalog,
    ProviderModelsRefreshRequest,
    ProviderModelsRefreshResponse,
)
from ..services.secret_storage_service import SecretStorageService
from ...services.execution_config import load_execution_runtime_config
from ...services.llm_provider_catalog import (
    SUPPORTED_LLM_PROVIDERS,
    all_provider_model_catalogs,
    normalize_llm_provider,
    provider_model_catalog,
    provider_requires_api_key,
)
from ...services.provider_model_refresh import (
    OPENROUTER_ACCOUNT_MODELS_URL,
    ProviderModelRefreshError,
    refresh_provider_model_catalog,
)
from ...services.model_registry import merge_refreshed_model_metadata
from .deps import ensure_appdata_principal, get_current_user

router = APIRouter(
    prefix="/preferences",
    tags=["V1 Preferences"],
    dependencies=[Depends(ensure_appdata_principal)],
)

_VERIFY_TIMEOUT_SECONDS = 20.0
_RECOMMENDED_FOR_ALLOWED = {"main", "lite", "both"}
_TAGS_ALLOWED = {"recommended", "extended"}


def _clean_models(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _clean_recommended_for(raw: Any) -> list[str]:
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, list):
        values = raw
    else:
        values = []

    cleaned: list[str] = []
    for item in values:
        value = str(item or "").strip().lower()
        if value in _RECOMMENDED_FOR_ALLOWED and value not in cleaned:
            cleaned.append(value)

    if not cleaned:
        return ["main"]
    if "both" in cleaned:
        return ["both"]
    return cleaned


def _clean_tags(raw: Any) -> list[str]:
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, list):
        values = raw
    else:
        values = []

    cleaned: list[str] = []
    for item in values:
        value = str(item or "").strip().lower()
        if value in _TAGS_ALLOWED and value not in cleaned:
            cleaned.append(value)

    if not cleaned:
        return ["recommended"]
    return cleaned


def _clean_model_metadata_entries(
    provider: str,
    raw: Any,
    fallback: Any,
) -> list[dict[str, Any]]:
    entries = raw if isinstance(raw, list) else fallback if isinstance(fallback, list) else []
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in entries:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)

        context_window_raw = item.get("context_window")
        try:
            context_window = int(context_window_raw)
        except Exception:  # noqa: BLE001
            context_window = 0
        if context_window < 0:
            context_window = 0

        cleaned.append(
            {
                "id": model_id,
                "display_name": str(item.get("display_name") or model_id).strip() or model_id,
                "provider": normalize_llm_provider(item.get("provider") or provider),
                "context_window": context_window,
                "recommended_for": _clean_recommended_for(item.get("recommended_for")),
                "tags": _clean_tags(item.get("tags")),
            }
        )

    return cleaned


def _coerce_provider_catalog(
    provider: str,
    raw_catalog: Any,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    data = raw_catalog if isinstance(raw_catalog, dict) else {}

    main_models = _clean_models(data.get("main_models"))
    if not main_models:
        main_models = _clean_models(fallback.get("main_models", []))

    default_main_model = str(data.get("default_main_model") or "").strip()
    if default_main_model not in main_models:
        fallback_default_main = str(fallback.get("default_main_model") or "").strip()
        default_main_model = (
            fallback_default_main if fallback_default_main in main_models else (main_models[0] if main_models else "")
        )

    lite_models = _clean_models(data.get("lite_models"))
    if not lite_models:
        lite_models = _clean_models(fallback.get("lite_models", []))
    if not lite_models and default_main_model:
        lite_models = [default_main_model]

    default_lite_model = str(data.get("default_lite_model") or "").strip()
    if default_lite_model not in lite_models:
        fallback_default_lite = str(fallback.get("default_lite_model") or "").strip()
        if fallback_default_lite in lite_models:
            default_lite_model = fallback_default_lite
        elif lite_models:
            default_lite_model = lite_models[0]
        else:
            default_lite_model = default_main_model

    source = str(data.get("source") or fallback.get("source") or "default").strip() or "default"

    account_models_configured: bool | None
    if data.get("account_models_configured") is None:
        account_models_configured = fallback.get("account_models_configured")
    else:
        account_models_configured = bool(data.get("account_models_configured"))

    account_models_url = str(
        data.get("account_models_url")
        or fallback.get("account_models_url")
        or (OPENROUTER_ACCOUNT_MODELS_URL if provider == "openrouter" else "")
    ).strip()

    models = _clean_model_metadata_entries(
        provider,
        data.get("models"),
        fallback.get("models"),
    )

    return {
        "main_models": main_models,
        "lite_models": lite_models,
        "default_main_model": default_main_model,
        "default_lite_model": default_lite_model,
        "source": source,
        "account_models_configured": account_models_configured,
        "account_models_url": account_models_url,
        "models": models,
    }


def _resolve_provider_catalogs(prefs) -> dict[str, dict[str, Any]]:
    base_catalogs = all_provider_model_catalogs()

    raw_overrides = {}
    try:
        parsed = json.loads(str(getattr(prefs, "provider_model_catalogs_json", "{}") or "{}"))
        if isinstance(parsed, dict):
            raw_overrides = parsed
    except Exception:  # noqa: BLE001
        raw_overrides = {}

    merged: dict[str, dict[str, Any]] = {}
    for provider in SUPPORTED_LLM_PROVIDERS:
        fallback = dict(base_catalogs.get(provider, provider_model_catalog(provider)))
        override = raw_overrides.get(provider)
        merged[provider] = _coerce_provider_catalog(provider, override, fallback)
    return merged


def _provider_env_api_key_present(provider: str) -> bool:
    normalized = normalize_llm_provider(provider)
    if normalized == "openai":
        return bool(str(os.getenv("OPENAI_API_KEY", "")).strip())
    if normalized == "anthropic":
        return bool(str(os.getenv("ANTHROPIC_API_KEY", "")).strip())
    if normalized == "ollama":
        return bool(str(os.getenv("OLLAMA_API_KEY", "")).strip())
    return bool(str(os.getenv("OPENROUTER_API_KEY", "")).strip())


def _merge_env_api_key_presence(api_key_presence: dict[str, bool]) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for provider in SUPPORTED_LLM_PROVIDERS:
        normalized = normalize_llm_provider(provider)
        merged[normalized] = bool(api_key_presence.get(normalized)) or _provider_env_api_key_present(normalized)
    return merged


def _load_enabled_models(raw_json: str, catalog: dict[str, Any]) -> list[str]:
    allowed = set(_clean_models(catalog.get("main_models", [])))
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
    return list(catalog.get("main_models", []))


def _normalize_model_preferences(prefs, provider_catalogs: dict[str, dict[str, Any]]) -> None:
    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))

    enabled_models = _load_enabled_models(
        getattr(prefs, "enabled_main_models_json", "[]"),
        catalog,
    )
    if not enabled_models:
        enabled_models = list(catalog.get("main_models", []))
    prefs.enabled_main_models_json = json.dumps(enabled_models)

    selected_model = str(getattr(prefs, "selected_model", "") or "").strip()
    if selected_model not in enabled_models:
        selected_model = str(catalog.get("default_main_model") or "").strip()
    if selected_model not in enabled_models:
        selected_model = enabled_models[0] if enabled_models else ""
    prefs.selected_model = selected_model

    lite_models = _clean_models(catalog.get("lite_models", []))
    selected_lite_model = str(getattr(prefs, "selected_lite_model", "") or "").strip()
    if selected_lite_model not in lite_models:
        fallback_lite = str(catalog.get("default_lite_model") or "").strip()
        if fallback_lite in lite_models:
            selected_lite_model = fallback_lite
        elif lite_models:
            selected_lite_model = lite_models[0]
        else:
            selected_lite_model = selected_model
    prefs.selected_lite_model = selected_lite_model

    selected_coding_model = str(getattr(prefs, "selected_coding_model", "") or "").strip()
    if selected_coding_model not in enabled_models:
        selected_coding_model = selected_model
    prefs.selected_coding_model = selected_coding_model


def _to_response(prefs, api_key_presence: dict[str, bool]) -> PreferencesResponse:
    api_key_presence = _merge_env_api_key_presence(api_key_presence)
    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    provider_catalogs = _resolve_provider_catalogs(prefs)
    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))

    enabled_models = _load_enabled_models(
        getattr(prefs, "enabled_main_models_json", "[]"),
        catalog,
    )
    selected_model = str(getattr(prefs, "selected_model", "") or "").strip()
    if selected_model not in enabled_models:
        selected_model = str(catalog.get("default_main_model") or "").strip()
    if selected_model not in enabled_models:
        selected_model = enabled_models[0] if enabled_models else ""

    selected_lite_model = str(getattr(prefs, "selected_lite_model", "") or "").strip()
    if selected_lite_model not in catalog.get("lite_models", []):
        selected_lite_model = str(catalog.get("default_lite_model") or "").strip()
    if selected_lite_model not in catalog.get("lite_models", []):
        selected_lite_model = selected_model

    selected_coding_model = str(getattr(prefs, "selected_coding_model", "") or "").strip()
    if selected_coding_model not in enabled_models:
        selected_coding_model = selected_model

    execution_runtime = load_execution_runtime_config()
    requires_api_key = provider_requires_api_key(provider)
    selected_key_present = bool(api_key_presence.get(provider))
    return PreferencesResponse(
        llm_provider=provider,
        available_providers=list(SUPPORTED_LLM_PROVIDERS),
        selected_model=selected_model,
        selected_lite_model=selected_lite_model,
        selected_coding_model=selected_coding_model,
        enabled_models=enabled_models,
        schema_context=prefs.schema_context,
        allow_schema_sample_values=bool(prefs.allow_schema_sample_values),
        terminal_risk_acknowledged=bool(getattr(prefs, "terminal_risk_acknowledged", False)),
        chat_overlay_width=float(prefs.chat_overlay_width),
        is_sidebar_collapsed=bool(prefs.is_sidebar_collapsed),
        hide_shortcuts_modal=bool(prefs.hide_shortcuts_modal),
        active_workspace_id=prefs.active_workspace_id,
        active_dataset_path=prefs.active_dataset_path,
        active_table_name=prefs.active_table_name,
        api_key_present=selected_key_present,
        available_models=enabled_models,
        provider_available_main_models=list(catalog.get("main_models", [])),
        provider_available_lite_models=list(catalog.get("lite_models", [])),
        provider_model_catalogs={
            p: ProviderModelCatalog(**c)
            for p, c in provider_catalogs.items()
        },
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
    provider_catalogs = _resolve_provider_catalogs(prefs)

    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))

    if payload.llm_provider is not None:
        provider = normalize_llm_provider(payload.llm_provider)
        prefs.llm_provider = provider
        catalog = provider_catalogs.get(provider, provider_model_catalog(provider))

    if payload.enabled_models is not None:
        allowed = set(catalog.get("main_models", []))
        cleaned: list[str] = []
        seen: set[str] = set()
        for model in payload.enabled_models:
            value = str(model or "").strip()
            if not value or value not in allowed or value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        prefs.enabled_main_models_json = json.dumps(
            cleaned or list(catalog.get("main_models", []))
        )

    enabled_models = _load_enabled_models(
        getattr(prefs, "enabled_main_models_json", "[]"),
        catalog,
    )
    if payload.selected_model is not None:
        selected_model = str(payload.selected_model or "").strip()
        if selected_model in enabled_models:
            prefs.selected_model = selected_model
    if payload.selected_lite_model is not None:
        selected_lite_model = str(payload.selected_lite_model or "").strip()
        if selected_lite_model in catalog.get("lite_models", []):
            prefs.selected_lite_model = selected_lite_model
    if payload.selected_coding_model is not None:
        selected_coding_model = str(payload.selected_coding_model or "").strip()
        if selected_coding_model in enabled_models:
            prefs.selected_coding_model = selected_coding_model
    if payload.schema_context is not None:
        prefs.schema_context = payload.schema_context
    if payload.allow_schema_sample_values is not None:
        prefs.allow_schema_sample_values = payload.allow_schema_sample_values
    if payload.terminal_risk_acknowledged is not None:
        prefs.terminal_risk_acknowledged = bool(payload.terminal_risk_acknowledged)
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

    _normalize_model_preferences(prefs, provider_catalogs)

    await session.commit()
    key_presence = SecretStorageService.get_api_key_presence_map(
        current_user.id, list(SUPPORTED_LLM_PROVIDERS)
    )
    return _to_response(prefs, key_presence)


@router.post("/models/refresh", response_model=ProviderModelsRefreshResponse)
async def refresh_provider_models(
    payload: ProviderModelsRefreshRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    provider_catalogs = _resolve_provider_catalogs(prefs)

    default_provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    provider = normalize_llm_provider(payload.provider or default_provider)

    api_key = str(payload.api_key or "").strip()
    if not api_key:
        api_key = str(SecretStorageService.get_api_key(current_user.id, provider=provider) or "").strip()

    try:
        refresh_result = await refresh_provider_model_catalog(
            provider,
            api_key=api_key,
            base_url=payload.base_url,
        )
    except ProviderModelRefreshError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    fallback = provider_catalogs.get(provider, provider_model_catalog(provider))
    merged_catalog = dict(refresh_result.catalog)
    merged_catalog["models"] = merge_refreshed_model_metadata(
        provider,
        fallback.get("models"),
        merged_catalog.get("main_models", []),
        merged_catalog.get("lite_models", []),
    )
    provider_catalogs[provider] = _coerce_provider_catalog(
        provider,
        merged_catalog,
        fallback,
    )
    prefs.provider_model_catalogs_json = json.dumps(provider_catalogs)

    _normalize_model_preferences(prefs, provider_catalogs)

    await session.commit()
    key_presence = SecretStorageService.get_api_key_presence_map(
        current_user.id, list(SUPPORTED_LLM_PROVIDERS)
    )
    response = _to_response(prefs, key_presence)
    return ProviderModelsRefreshResponse(
        **response.model_dump(),
        detail=refresh_result.detail,
        error=refresh_result.error,
    )


def _verify_error_from_status(status_code: int) -> str:
    if status_code == 429:
        return "quota_exceeded"
    if status_code in {401, 403}:
        return "invalid_key"
    return "network_error"


@router.post("/verify-key", response_model=ApiKeyVerifyResponse)
async def verify_api_key(
    payload: ApiKeyVerifyRequest,
) -> ApiKeyVerifyResponse:
    provider = normalize_llm_provider(payload.provider)
    key = str(payload.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    if provider not in {"openai", "openrouter"}:
        raise HTTPException(
            status_code=400,
            detail="Only openai and openrouter support API key verification.",
        )

    url = "https://api.openai.com/v1/models" if provider == "openai" else "https://openrouter.ai/api/v1/auth/key"
    headers = {"Authorization": f"Bearer {key}"}

    try:
        async with httpx.AsyncClient(timeout=_VERIFY_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError:
        return ApiKeyVerifyResponse(valid=False, error="network_error")

    status_code = int(getattr(response, "status_code", 0) or 0)
    if 200 <= status_code < 300:
        return ApiKeyVerifyResponse(valid=True, error="")

    return ApiKeyVerifyResponse(valid=False, error=_verify_error_from_status(status_code))


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
        raise HTTPException(
            status_code=500, detail="Failed to persist API key in OS keychain."
        ) from exc
    return MessageResponse(
        message=f"API key for provider '{provider}' saved to OS keychain."
    )


@router.delete("/api-key", response_model=MessageResponse)
async def delete_api_key(
    provider: str | None = None,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    default_provider = str(getattr(prefs, "llm_provider", "openrouter") or "openrouter")
    selected_provider = normalize_llm_provider(str(provider or default_provider))
    try:
        SecretStorageService.delete_api_key(current_user.id, provider=selected_provider)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail="Failed to remove API key from OS keychain."
        ) from exc
    return MessageResponse(
        message=f"API key for provider '{selected_provider}' removed from OS keychain."
    )
