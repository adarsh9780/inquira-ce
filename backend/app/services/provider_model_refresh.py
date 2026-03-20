"""Remote provider model catalog refresh utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .llm_provider_catalog import normalize_llm_provider, provider_model_catalog

OPENROUTER_ACCOUNT_MODELS_URL = "https://openrouter.ai/settings"
_REQUEST_TIMEOUT_SECONDS = 20.0
_LITE_MODEL_HINTS: tuple[str, ...] = (
    "nano",
    "mini",
    "haiku",
    "lite",
    "small",
    ":3b",
    ":2b",
    "flash-lite",
    "free",
)


class ProviderModelRefreshError(RuntimeError):
    """Structured refresh error that can be mapped to HTTP responses."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = str(detail)
        self.status_code = int(status_code)


@dataclass(slots=True)
class ProviderRefreshResult:
    provider: str
    catalog: dict[str, Any]
    detail: str


async def refresh_provider_model_catalog(provider: str, api_key: str | None = None) -> ProviderRefreshResult:
    """Fetch provider model IDs and convert them into a settings catalog payload."""
    normalized_provider = normalize_llm_provider(provider)
    fallback_catalog = provider_model_catalog(normalized_provider)

    if normalized_provider == "ollama":
        catalog = {
            **fallback_catalog,
            "source": "default",
        }
        return ProviderRefreshResult(
            provider=normalized_provider,
            catalog=catalog,
            detail="Ollama uses local models; refreshed using local defaults.",
        )

    key = str(api_key or "").strip()
    if not key:
        raise ProviderModelRefreshError(
            f"API key is required to refresh models for provider '{normalized_provider}'.",
            status_code=400,
        )

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            if normalized_provider == "openai":
                main_models = await _fetch_openai_models(client, key)
                catalog = _build_catalog(normalized_provider, main_models)
                return ProviderRefreshResult(
                    provider=normalized_provider,
                    catalog=catalog,
                    detail=f"Refreshed {len(catalog['main_models'])} OpenAI models.",
                )

            if normalized_provider == "anthropic":
                main_models = await _fetch_anthropic_models(client, key)
                catalog = _build_catalog(normalized_provider, main_models)
                return ProviderRefreshResult(
                    provider=normalized_provider,
                    catalog=catalog,
                    detail=f"Refreshed {len(catalog['main_models'])} Anthropic models.",
                )

            if normalized_provider == "openrouter":
                main_models, account_models_configured = await _fetch_openrouter_account_models(
                    client,
                    key,
                )
                catalog = _build_catalog(
                    normalized_provider,
                    main_models,
                    account_models_configured=account_models_configured,
                    account_models_url=OPENROUTER_ACCOUNT_MODELS_URL,
                )
                if not account_models_configured:
                    detail = (
                        "OpenRouter account-level models are not configured. "
                        "Using openrouter/free by default."
                    )
                else:
                    detail = f"Refreshed {len(catalog['main_models'])} OpenRouter account models."
                return ProviderRefreshResult(
                    provider=normalized_provider,
                    catalog=catalog,
                    detail=detail,
                )

    except httpx.HTTPStatusError as exc:
        status_code = int(getattr(exc.response, "status_code", 502) or 502)
        detail = _provider_http_error_message(normalized_provider, status_code)
        raise ProviderModelRefreshError(detail, status_code=status_code) from exc
    except httpx.HTTPError as exc:
        raise ProviderModelRefreshError(
            f"Unable to refresh models from provider '{normalized_provider}': {exc}",
            status_code=502,
        ) from exc

    raise ProviderModelRefreshError(
        f"Unsupported provider '{normalized_provider}'.",
        status_code=400,
    )


def _provider_http_error_message(provider: str, status_code: int) -> str:
    if status_code in {401, 403}:
        return f"Provider '{provider}' rejected the API key while refreshing models."
    if status_code == 429:
        return f"Provider '{provider}' rate-limited model refresh. Please try again shortly."
    return f"Provider '{provider}' failed to return model catalog (HTTP {status_code})."


async def _fetch_openai_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    response = await client.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    response.raise_for_status()
    payload = response.json()
    raw_models = []
    for item in _extract_data_list(payload):
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        if _is_openai_chat_model(model_id):
            raw_models.append(model_id)
    return _unique_models(raw_models)


async def _fetch_anthropic_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    response = await client.get(
        "https://api.anthropic.com/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )
    response.raise_for_status()
    payload = response.json()
    raw_models = []
    for item in _extract_data_list(payload):
        model_id = str(item.get("id") or "").strip()
        if model_id.startswith("claude"):
            raw_models.append(model_id)
    return _unique_models(raw_models)


async def _fetch_openrouter_account_models(
    client: httpx.AsyncClient,
    api_key: str,
) -> tuple[list[str], bool]:
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    models_response = await client.get(
        "https://openrouter.ai/api/v1/models",
        headers=headers,
    )
    models_response.raise_for_status()
    models_payload = models_response.json()
    all_models = _unique_models(
        [
            str(item.get("id") or "").strip()
            for item in _extract_data_list(models_payload)
            if str(item.get("id") or "").strip()
        ]
    )

    key_response = await client.get(
        "https://openrouter.ai/api/v1/auth/key",
        headers=headers,
    )
    key_response.raise_for_status()
    key_payload = key_response.json()
    configured_models = _extract_openrouter_account_model_ids(key_payload)

    if not configured_models:
        return ["openrouter/free"], False

    available = set(all_models)
    filtered = [model_id for model_id in configured_models if model_id in available]
    if not filtered:
        filtered = configured_models

    return _unique_models(filtered), True


def _extract_openrouter_account_model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    candidates: list[Any] = [
        data.get("allowed_models"),
        data.get("models"),
        data.get("permitted_models"),
        data.get("model_ids"),
    ]
    model_preferences = data.get("model_preferences")
    if isinstance(model_preferences, dict):
        candidates.append(model_preferences.get("models"))

    for candidate in candidates:
        if isinstance(candidate, list):
            return _unique_models([str(item or "").strip() for item in candidate])

    return []


def _build_catalog(
    provider: str,
    main_models: list[str],
    *,
    account_models_configured: bool | None = None,
    account_models_url: str = "",
) -> dict[str, Any]:
    normalized_provider = normalize_llm_provider(provider)
    fallback = provider_model_catalog(normalized_provider)

    cleaned_main = _unique_models(main_models)
    if not cleaned_main:
        cleaned_main = _unique_models(fallback["main_models"])

    if normalized_provider == "openrouter" and account_models_configured is False:
        cleaned_main = ["openrouter/free"]

    if not cleaned_main:
        cleaned_main = [str(fallback["default_main_model"]).strip()]

    default_main_model = str(fallback.get("default_main_model") or "").strip()
    if default_main_model not in cleaned_main:
        default_main_model = cleaned_main[0]

    lite_candidates = [
        model_id
        for model_id in cleaned_main
        if any(hint in model_id.lower() for hint in _LITE_MODEL_HINTS)
    ]
    if not lite_candidates and default_main_model:
        lite_candidates = [default_main_model]

    default_lite_model = str(fallback.get("default_lite_model") or "").strip()
    if default_lite_model in cleaned_main:
        lite_candidates.insert(0, default_lite_model)

    lite_models = _unique_models(lite_candidates)
    if not lite_models:
        lite_models = [cleaned_main[0]]

    default_lite_model = default_lite_model if default_lite_model in lite_models else lite_models[0]

    catalog: dict[str, Any] = {
        "main_models": cleaned_main,
        "lite_models": lite_models,
        "default_main_model": default_main_model,
        "default_lite_model": default_lite_model,
        "source": "refreshed",
    }

    if account_models_configured is not None:
        catalog["account_models_configured"] = bool(account_models_configured)
    if account_models_url:
        catalog["account_models_url"] = str(account_models_url).strip()

    return catalog


def _extract_data_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _is_openai_chat_model(model_id: str) -> bool:
    value = str(model_id or "").strip().lower()
    if not value:
        return False

    blocked_tokens = (
        "embedding",
        "whisper",
        "moderation",
        "tts",
        "transcribe",
        "gpt-image",
        "dall",
        "omni-moderation",
    )
    if any(token in value for token in blocked_tokens):
        return False

    allowed_prefixes = (
        "gpt",
        "o1",
        "o3",
        "o4",
        "chatgpt",
    )
    return value.startswith(allowed_prefixes)


def _unique_models(models: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for model in models:
        value = str(model or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned
