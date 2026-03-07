"""Provider defaults and curated model catalogs for settings UX."""

from __future__ import annotations

from typing import Any

SUPPORTED_LLM_PROVIDERS: tuple[str, ...] = (
    "openrouter",
    "openai",
    "anthropic",
    "ollama",
)

_DEFAULT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "",
    "ollama": "http://localhost:11434/v1",
}

_MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "openrouter": {
        "main_models": [
            "google/gemini-3-flash-preview",
            "google/gemini-2.5-flash",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "openrouter/free",
        ],
        "lite_models": [
            "google/gemini-2.5-flash-lite",
            "openai/gpt-4.1-nano",
        ],
        "default_main_model": "google/gemini-2.5-flash",
        "default_lite_model": "google/gemini-2.5-flash-lite",
    },
    "openai": {
        "main_models": [
            "gpt-4.1",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        "lite_models": [
            "gpt-4.1-mini",
            "gpt-4.1-nano",
        ],
        "default_main_model": "gpt-4o-mini",
        "default_lite_model": "gpt-4.1-mini",
    },
    "anthropic": {
        "main_models": [
            "claude-3-5-sonnet-latest",
            "claude-3-7-sonnet-latest",
        ],
        "lite_models": [
            "claude-3-5-haiku-latest",
        ],
        "default_main_model": "claude-3-5-sonnet-latest",
        "default_lite_model": "claude-3-5-haiku-latest",
    },
    "ollama": {
        "main_models": [
            "llama3.2",
            "qwen2.5-coder:7b",
            "mistral",
            "deepseek-r1:8b",
        ],
        "lite_models": [
            "llama3.2:3b",
            "qwen2.5:3b",
        ],
        "default_main_model": "llama3.2",
        "default_lite_model": "llama3.2:3b",
    },
}


def normalize_llm_provider(provider: str) -> str:
    value = str(provider or "").strip().lower()
    if value in SUPPORTED_LLM_PROVIDERS:
        return value
    return "openrouter"


def provider_requires_api_key(provider: str) -> bool:
    return normalize_llm_provider(provider) != "ollama"


def provider_default_base_url(provider: str) -> str:
    return _DEFAULT_BASE_URLS.get(normalize_llm_provider(provider), _DEFAULT_BASE_URLS["openrouter"])


def provider_model_catalog(provider: str) -> dict[str, Any]:
    normalized = normalize_llm_provider(provider)
    catalog = _MODEL_CATALOG.get(normalized, _MODEL_CATALOG["openrouter"])
    return {
        "main_models": list(catalog["main_models"]),
        "lite_models": list(catalog["lite_models"]),
        "default_main_model": str(catalog["default_main_model"]),
        "default_lite_model": str(catalog["default_lite_model"]),
    }


def all_provider_model_catalogs() -> dict[str, dict[str, Any]]:
    return {provider: provider_model_catalog(provider) for provider in SUPPORTED_LLM_PROVIDERS}
