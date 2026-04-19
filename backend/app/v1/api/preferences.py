"""API v1 user preferences and keychain-backed API key routes."""

from __future__ import annotations

import json
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
    ProviderConfigSaveResponse,
    ProviderModelEntry,
    PreferencesResponse,
    PreferencesUpdateRequest,
    ProviderModelCatalog,
    ProviderModelsSearchResponse,
    ProviderModelsRefreshRequest,
    ProviderModelsRefreshResponse,
)
from ..services.secret_storage_service import SecretStorageService
from ...services.execution_config import load_execution_runtime_config
from ...services.llm_provider_catalog import (
    SUPPORTED_LLM_PROVIDERS,
    all_provider_model_catalogs,
    normalize_llm_provider,
    provider_default_base_url,
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
_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_PROVIDER_MODEL_LIMIT = 100
OPENROUTER_DEFAULT_PREFIXES = ("google/", "openai/", "anthropic/")


def _coerce_non_negative_int(raw: Any) -> int:
    if raw is None:
        return 0
    try:
        value = int(raw)
    except Exception:  # noqa: BLE001
        return 0
    if value < 0:
        return 0
    return value


def _model_allowed_for_provider(provider: str, model_id: str) -> bool:
    normalized_provider = normalize_llm_provider(provider)
    value = str(model_id or "").strip().lower()
    if not value:
        return False
    if normalized_provider != "ollama" and ":cloud" in value:
        return False
    return True


def _clean_models(raw: Any, provider: str = "") -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        if provider and not _model_allowed_for_provider(provider, value):
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
        if not _model_allowed_for_provider(provider, model_id):
            continue
        seen.add(model_id)

        context_window = _coerce_non_negative_int(item.get("context_window"))

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


def _dedupe_models(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        model_id = str(value or "").strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        cleaned.append(model_id)
    return cleaned


def _provider_display_main_models(
    provider: str,
    catalog: dict[str, Any],
    selected_model: str | None = None,
    limit: int = DEFAULT_PROVIDER_MODEL_LIMIT,
) -> list[str]:
    normalized_provider = normalize_llm_provider(provider)
    main_models = _clean_models(catalog.get("main_models", []), normalized_provider)
    max_results = max(1, int(limit or DEFAULT_PROVIDER_MODEL_LIMIT))

    if normalized_provider == "openrouter":
        display_models = [
            model_id
            for model_id in main_models
            if model_id.lower().startswith(OPENROUTER_DEFAULT_PREFIXES)
        ]
    else:
        display_models = list(main_models)

    display_models = _dedupe_models(display_models)[:max_results]

    selected = str(selected_model or "").strip()
    if selected and selected in main_models and selected not in display_models:
        display_models = [selected, *display_models]

    return _dedupe_models(display_models)[:max_results]


def _model_entry_matches_query(entry: dict[str, Any], query: str) -> bool:
    normalized = str(query or "").strip().lower()
    if not normalized:
        return False

    candidates = [
        entry.get("id"),
        entry.get("display_name"),
        entry.get("provider"),
        entry.get("context_window"),
        entry.get("recommended_for"),
        entry.get("tags"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            haystack = " ".join(str(item or "").strip().lower() for item in candidate)
        else:
            haystack = str(candidate or "").strip().lower()
        if haystack and normalized in haystack:
            return True
    return False


def _search_provider_models(
    provider: str,
    query: str,
    catalog: dict[str, Any],
    limit: int = 25,
) -> list[ProviderModelEntry]:
    normalized_provider = normalize_llm_provider(provider)
    needle = str(query or "").strip().lower()
    if len(needle) < 2:
        return []

    max_results = max(1, min(int(limit or 25), 50))
    raw_entries = catalog.get("models", [])
    entries: list[dict[str, Any]] = []
    if isinstance(raw_entries, list):
        entries = [item for item in raw_entries if isinstance(item, dict)]

    if not entries:
        entries = [
            {
                "id": model_id,
                "display_name": model_id,
                "provider": normalized_provider,
                "context_window": 0,
                "recommended_for": ["main"],
                "tags": ["recommended"],
            }
            for model_id in _clean_models(catalog.get("main_models", []), normalized_provider)
        ]

    results: list[ProviderModelEntry] = []
    seen: set[str] = set()
    for entry in entries:
        model_id = str(entry.get("id") or "").strip()
        if not model_id or model_id in seen:
            continue
        entry_provider = normalize_llm_provider(entry.get("provider") or normalized_provider)
        if entry_provider != normalized_provider:
            continue
        if not _model_allowed_for_provider(normalized_provider, model_id):
            continue
        if not _model_entry_matches_query(entry, needle):
            continue
        seen.add(model_id)
        results.append(
            ProviderModelEntry(
                id=model_id,
                display_name=str(entry.get("display_name") or model_id).strip() or model_id,
                provider=normalized_provider,
                context_window=_coerce_non_negative_int(entry.get("context_window")),
                recommended_for=_clean_recommended_for(entry.get("recommended_for")),
                tags=_clean_tags(entry.get("tags")),
            )
        )
        if len(results) >= max_results:
            break

    return results


def _coerce_provider_catalog(
    provider: str,
    raw_catalog: Any,
    fallback: dict[str, Any],
) -> dict[str, Any]:
    data = raw_catalog if isinstance(raw_catalog, dict) else {}

    main_models = _clean_models(data.get("main_models"), provider)
    if not main_models:
        main_models = _clean_models(fallback.get("main_models", []), provider)

    default_main_model = str(data.get("default_main_model") or "").strip()
    if default_main_model not in main_models:
        fallback_default_main = str(fallback.get("default_main_model") or "").strip()
        default_main_model = (
            fallback_default_main if fallback_default_main in main_models else (main_models[0] if main_models else "")
        )

    lite_models = _clean_models(data.get("lite_models"), provider)
    if not lite_models:
        lite_models = _clean_models(fallback.get("lite_models", []), provider)
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
    base_url = str(data.get("base_url") or fallback.get("base_url") or "").strip()
    if provider == "ollama":
        default_base = str(provider_default_base_url("ollama") or "").strip() or _DEFAULT_OLLAMA_BASE_URL
        if default_base.endswith("/v1"):
            default_base = default_base[:-3].rstrip("/")
        if default_base.endswith("/api"):
            default_base = default_base[:-4].rstrip("/")
        normalized_base = base_url.rstrip("/")
        if not normalized_base:
            normalized_base = default_base.rstrip("/")
        base_url = normalized_base or _DEFAULT_OLLAMA_BASE_URL

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
        "base_url": base_url,
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


def _normalize_api_key_presence(api_key_presence: dict[str, bool]) -> dict[str, bool]:
    merged: dict[str, bool] = {}
    for provider in SUPPORTED_LLM_PROVIDERS:
        normalized = normalize_llm_provider(provider)
        merged[normalized] = bool(api_key_presence.get(normalized))
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

    enabled_models = _clean_models(catalog.get("main_models", []), provider)
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
    api_key_presence = _normalize_api_key_presence(api_key_presence)
    provider = normalize_llm_provider(getattr(prefs, "llm_provider", "openrouter"))
    provider_catalogs = _resolve_provider_catalogs(prefs)
    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))

    enabled_models = _clean_models(catalog.get("main_models", []), provider)
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
    display_models = _provider_display_main_models(provider, catalog, selected_model=selected_model)
    return PreferencesResponse(
        llm_provider=provider,
        available_providers=list(SUPPORTED_LLM_PROVIDERS),
        selected_model=selected_model,
        selected_lite_model=selected_lite_model,
        selected_coding_model=selected_coding_model,
        llm_temperature=float(getattr(prefs, "llm_temperature", 0.7)),
        llm_max_tokens=int(getattr(prefs, "llm_max_tokens", 4096)),
        llm_top_p=float(getattr(prefs, "llm_top_p", 1.0)),
        llm_top_k=int(getattr(prefs, "llm_top_k", 0)),
        llm_frequency_penalty=float(getattr(prefs, "llm_frequency_penalty", 0.0)),
        llm_presence_penalty=float(getattr(prefs, "llm_presence_penalty", 0.0)),
        slow_request_warning_seconds=int(
            getattr(prefs, "slow_request_warning_seconds", 30)
        ),
        enabled_models=display_models,
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
        available_models=display_models,
        provider_available_main_models=display_models,
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


def _resolved_ollama_base_url(base_url: str | None) -> str:
    return str(base_url or "").strip().rstrip("/") or _DEFAULT_OLLAMA_BASE_URL


def _apply_refreshed_provider_catalog(
    provider: str,
    provider_catalogs: dict[str, dict[str, Any]],
    refreshed_catalog: dict[str, Any],
    *,
    base_url: str | None = None,
) -> None:
    fallback = provider_catalogs.get(provider, provider_model_catalog(provider))
    merged_catalog = dict(refreshed_catalog)
    if provider == "ollama":
        merged_catalog["base_url"] = _resolved_ollama_base_url(base_url)

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

    enabled_models = _clean_models(catalog.get("main_models", []), provider)
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
    if payload.llm_temperature is not None:
        prefs.llm_temperature = float(payload.llm_temperature)
    if payload.llm_max_tokens is not None:
        prefs.llm_max_tokens = int(payload.llm_max_tokens)
    if payload.llm_top_p is not None:
        prefs.llm_top_p = float(payload.llm_top_p)
    if payload.llm_top_k is not None:
        prefs.llm_top_k = int(payload.llm_top_k)
    if payload.llm_frequency_penalty is not None:
        prefs.llm_frequency_penalty = float(payload.llm_frequency_penalty)
    if payload.llm_presence_penalty is not None:
        prefs.llm_presence_penalty = float(payload.llm_presence_penalty)
    if payload.slow_request_warning_seconds is not None:
        prefs.slow_request_warning_seconds = int(payload.slow_request_warning_seconds)
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

    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))
    refresh_base_url = payload.base_url
    if provider == "ollama":
        refresh_base_url = str(payload.base_url or catalog.get("base_url") or _DEFAULT_OLLAMA_BASE_URL).strip()

    try:
        refresh_result = await refresh_provider_model_catalog(
            provider,
            api_key=api_key,
            base_url=refresh_base_url,
        )
    except ProviderModelRefreshError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    _apply_refreshed_provider_catalog(
        provider,
        provider_catalogs,
        refresh_result.catalog,
        base_url=refresh_base_url,
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


async def _verify_provider_api_key(provider: str, api_key: str) -> ApiKeyVerifyResponse:
    normalized_provider = normalize_llm_provider(provider)
    key = str(api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    if normalized_provider not in {"openai", "openrouter"}:
        raise HTTPException(
            status_code=400,
            detail="Only openai and openrouter support API key verification.",
        )

    url = "https://api.openai.com/v1/models" if normalized_provider == "openai" else "https://openrouter.ai/api/v1/auth/key"
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


async def _verify_provider_api_key_or_raise(provider: str, api_key: str) -> None:
    verify_result = await _verify_provider_api_key(provider, api_key)
    if verify_result.valid:
        return

    code = str(verify_result.error or "invalid_key").strip() or "invalid_key"
    detail = "Invalid API key."
    if code == "quota_exceeded":
        detail = "Key is valid but quota is exceeded for this provider."
    elif code == "network_error":
        detail = "Could not reach provider. Check your connection and try again."
    raise HTTPException(status_code=400, detail=detail)


@router.post("/verify-key", response_model=ApiKeyVerifyResponse)
async def verify_api_key(
    payload: ApiKeyVerifyRequest,
) -> ApiKeyVerifyResponse:
    return await _verify_provider_api_key(payload.provider, payload.api_key)


@router.get("/models/search", response_model=ProviderModelsSearchResponse)
async def search_provider_models(
    provider: str | None = None,
    q: str = "",
    limit: int = 25,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    provider_catalogs = _resolve_provider_catalogs(prefs)
    raw_provider = provider if provider is not None else str(getattr(prefs, "llm_provider", "openrouter") or "openrouter")
    normalized_provider = normalize_llm_provider(str(raw_provider))
    catalog = provider_catalogs.get(normalized_provider, provider_model_catalog(normalized_provider))
    models = _search_provider_models(normalized_provider, q, catalog, limit=limit)
    return ProviderModelsSearchResponse(
        provider=normalized_provider,
        query=str(q or "").strip(),
        models=models,
        detail=f"Found {len(models)} models.",
        error="",
    )


@router.put("/api-key", response_model=ProviderConfigSaveResponse)
async def set_api_key(
    payload: ApiKeyUpdateRequest,
    session: AsyncSession = Depends(get_appdata_db_session),
    current_user=Depends(get_current_user),
):
    provider = normalize_llm_provider(payload.provider)
    prefs = await PreferencesRepository.get_or_create(session, current_user.id)
    provider_catalogs = _resolve_provider_catalogs(prefs)
    prefs.llm_provider = provider
    catalog = provider_catalogs.get(provider, provider_model_catalog(provider))
    api_key = str(payload.api_key or "").strip()
    stored_api_key = ""
    if not api_key and provider != "ollama":
        stored_api_key = str(SecretStorageService.get_api_key(current_user.id, provider=provider) or "").strip()

    refresh_api_key = api_key or stored_api_key
    refresh_base_url = payload.base_url
    refresh_warning = ""
    refresh_detail = ""

    if provider != "ollama":
        if api_key:
            await _verify_provider_api_key_or_raise(provider, api_key)
            try:
                SecretStorageService.set_api_key(current_user.id, api_key, provider=provider)
            except RuntimeError as exc:
                raise HTTPException(status_code=501, detail=str(exc)) from exc
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=500, detail="Failed to persist API key in OS keychain."
                ) from exc
            refresh_api_key = api_key
        elif not refresh_api_key:
            raise HTTPException(
                status_code=400,
                detail=f"API key is required to save configuration for provider '{provider}'.",
            )
    else:
        refresh_base_url = _resolved_ollama_base_url(payload.base_url)
        refresh_api_key = ""

    if payload.selected_model is not None:
        selected_model = str(payload.selected_model or "").strip()
        if selected_model in _clean_models(catalog.get("main_models", []), provider):
            prefs.selected_model = selected_model
    if payload.selected_lite_model is not None:
        selected_lite_model = str(payload.selected_lite_model or "").strip()
        if selected_lite_model in catalog.get("lite_models", []):
            prefs.selected_lite_model = selected_lite_model
    if payload.selected_coding_model is not None:
        selected_coding_model = str(payload.selected_coding_model or "").strip()
        if selected_coding_model in _clean_models(catalog.get("main_models", []), provider):
            prefs.selected_coding_model = selected_coding_model

    if payload.llm_temperature is not None:
        prefs.llm_temperature = float(payload.llm_temperature)
    if payload.llm_max_tokens is not None:
        prefs.llm_max_tokens = int(payload.llm_max_tokens)
    if payload.llm_top_p is not None:
        prefs.llm_top_p = float(payload.llm_top_p)
    if payload.llm_top_k is not None:
        prefs.llm_top_k = int(payload.llm_top_k)
    if payload.llm_frequency_penalty is not None:
        prefs.llm_frequency_penalty = float(payload.llm_frequency_penalty)
    if payload.llm_presence_penalty is not None:
        prefs.llm_presence_penalty = float(payload.llm_presence_penalty)
    if payload.slow_request_warning_seconds is not None:
        prefs.slow_request_warning_seconds = int(payload.slow_request_warning_seconds)

    try:
        refresh_result = await refresh_provider_model_catalog(
            provider,
            api_key=refresh_api_key or None,
            base_url=refresh_base_url,
        )
    except ProviderModelRefreshError as exc:
        if provider != "ollama" and refresh_api_key:
            refresh_warning = "API key saved, but model refresh failed. Using previous catalog."
            refresh_detail = f"Configuration for provider '{provider}' saved."
        else:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    else:
        if provider == "ollama" and refresh_result.error:
            raise HTTPException(status_code=400, detail=refresh_result.detail)
        _apply_refreshed_provider_catalog(
            provider,
            provider_catalogs,
            refresh_result.catalog,
            base_url=refresh_base_url,
        )
        prefs.provider_model_catalogs_json = json.dumps(provider_catalogs)
        refresh_detail = refresh_result.detail

    _normalize_model_preferences(prefs, provider_catalogs)

    await session.commit()
    key_presence = SecretStorageService.get_api_key_presence_map(
        current_user.id, list(SUPPORTED_LLM_PROVIDERS)
    )
    response = _to_response(prefs, key_presence)
    return ProviderConfigSaveResponse(
        **response.model_dump(),
        detail=refresh_detail or f"Configuration for provider '{provider}' saved.",
        warning=refresh_warning,
        error="",
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
