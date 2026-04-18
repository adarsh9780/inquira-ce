"""Remote provider model catalog refresh utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx

from .llm_provider_catalog import (
    normalize_llm_provider,
    provider_default_base_url,
    provider_model_catalog,
)

OPENROUTER_ACCOUNT_MODELS_URL = "https://openrouter.ai/settings"
OLLAMA_CLOUD_TAGS_URL = "https://ollama.com/api/tags"
OLLAMA_CLOUD_API_KEY_ENV = "OLLAMA_API_KEY"
_REQUEST_TIMEOUT_SECONDS = 20.0
_CURATED_OPENROUTER_MAIN_MODELS: tuple[str, ...] = (
    "google/gemini-2.5-flash",
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4-5",
)
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
    error: str = ""


async def refresh_provider_model_catalog(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
) -> ProviderRefreshResult:
    """Fetch provider model IDs and convert them into a settings catalog payload."""
    normalized_provider = normalize_llm_provider(provider)
    fallback_catalog = provider_model_catalog(normalized_provider)

    if normalized_provider == "ollama":
        resolved_base_url = str(base_url or provider_default_base_url("ollama")).strip() or "http://localhost:11434/v1"
        tags_url = _resolve_ollama_tags_url(resolved_base_url)
        key = str(api_key or "").strip() or str(os.getenv(OLLAMA_CLOUD_API_KEY_ENV) or "").strip()
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                local_models = await _fetch_ollama_models(client, tags_url)
                cloud_models = await _fetch_ollama_cloud_models(client, key)
                models = _unique_models([*local_models, *cloud_models])
                catalog = _build_catalog(normalized_provider, models)
                model_count = len(catalog["main_models"])
                if local_models and cloud_models:
                    detail = (
                        f"Refreshed {model_count} Ollama models "
                        f"({len(local_models)} local + {len(cloud_models)} cloud)."
                    )
                elif cloud_models:
                    detail = f"Refreshed {model_count} Ollama cloud models."
                else:
                    detail = f"Refreshed {model_count} Ollama models."
                return ProviderRefreshResult(
                    provider=normalized_provider,
                    catalog=catalog,
                    detail=detail,
                )
        except httpx.HTTPStatusError:
            return ProviderRefreshResult(
                provider=normalized_provider,
                catalog={**fallback_catalog, "source": "default"},
                detail=f"Ollama not detected at '{resolved_base_url}'. Is it running?",
                error="ollama_unreachable",
            )
        except httpx.HTTPError:
            return ProviderRefreshResult(
                provider=normalized_provider,
                catalog={**fallback_catalog, "source": "default"},
                detail=f"Ollama not detected at '{resolved_base_url}'. Is it running?",
                error="ollama_unreachable",
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
                if not account_models_configured:
                    main_models = list(_CURATED_OPENROUTER_MAIN_MODELS)
                catalog = _build_catalog(
                    normalized_provider,
                    main_models,
                    account_models_configured=account_models_configured,
                    account_models_url=OPENROUTER_ACCOUNT_MODELS_URL,
                )
                if not account_models_configured and catalog.get("main_models"):
                    catalog["default_main_model"] = str(catalog["main_models"][0]).strip()
                    if catalog.get("lite_models"):
                        catalog["default_lite_model"] = str(catalog["lite_models"][0]).strip()
                if not account_models_configured:
                    detail = (
                        "OpenRouter account-level models are not configured. "
                        "Using curated OpenRouter defaults."
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


def _resolve_ollama_tags_url(base_url: str) -> str:
    raw = str(base_url or "").strip().rstrip("/")
    if not raw:
        return "http://localhost:11434/api/tags"

    if raw.endswith("/v1"):
        raw = raw[:-3]

    if raw.endswith("/api"):
        return f"{raw}/tags"

    if raw.endswith("/api/tags"):
        return raw

    return urljoin(f"{raw}/", "api/tags")


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


async def _fetch_ollama_models(client: httpx.AsyncClient, tags_url: str) -> list[str]:
    response = await client.get(tags_url)
    response.raise_for_status()
    return _extract_ollama_models_from_tags_payload(response.json())


async def _fetch_ollama_cloud_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = await client.get(OLLAMA_CLOUD_TAGS_URL, headers=headers or None)
    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code in {401, 403}:
        return []

    response.raise_for_status()
    raw_models = _extract_ollama_models_from_tags_payload(response.json())
    return _unique_models([_normalize_ollama_cloud_model_id(model_id) for model_id in raw_models])


def _extract_ollama_models_from_tags_payload(payload: Any) -> list[str]:
    raw_models: list[str] = []
    models = payload.get("models") if isinstance(payload, dict) else None
    if isinstance(models, list):
        for item in models:
            if not isinstance(item, dict):
                continue
            # Prefer `model` when both are present. Ollama cloud responses can
            # include canonical IDs (for example, `minimax-m2.7:cloud`) in
            # `model` while `name` may be a shortened display value.
            model_id = str(item.get("model") or item.get("name") or "").strip()
            if model_id:
                raw_models.append(model_id)
    return _unique_models(raw_models)


def _normalize_ollama_cloud_model_id(model_id: str) -> str:
    value = str(model_id or "").strip()
    if not value:
        return ""
    # Ollama cloud often returns bare names (for example, "minimax-m2.7").
    # OpenAI-compatible chat calls typically require the cloud-qualified ID.
    if ":" in value:
        return value
    return f"{value}:cloud"


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

    # Prefer OpenRouter's user-filtered list (respects provider preferences/guardrails).
    # Fallback to /models only when older deployments do not expose /models/user.
    models_response = await client.get(
        "https://openrouter.ai/api/v1/models/user",
        headers=headers,
    )
    if int(getattr(models_response, "status_code", 0) or 0) == 404:
        models_response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
        )
    models_response.raise_for_status()
    models_payload = models_response.json()
    user_models = _unique_models(
        [
            str(item.get("id") or "").strip()
            for item in _extract_data_list(models_payload)
            if str(item.get("id") or "").strip()
        ]
    )

    if not user_models:
        return [], False

    return user_models, True


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
