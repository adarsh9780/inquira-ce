"""Provider defaults and curated model catalogs for settings UX."""

from __future__ import annotations

import copy
from functools import lru_cache
from typing import Any

from .model_registry import provider_catalog_from_registry

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
            "openai/gpt-4o",
            "anthropic/claude-sonnet-4-5",
        ],
        "lite_models": [
            "google/gemini-2.0-flash-001",
        ],
        "default_main_model": "openai/gpt-4o",
        "default_lite_model": "google/gemini-2.0-flash-001",
    },
    "openai": {
        "main_models": [
            "gpt-4.1",
            "gpt-4o",
        ],
        "lite_models": [
            "gpt-4.1-mini",
            "gpt-4o-mini",
        ],
        "default_main_model": "gpt-4.1",
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
            "gemma2:2b",
            "gemma2:9b",
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
    return _DEFAULT_BASE_URLS.get(
        normalize_llm_provider(provider), _DEFAULT_BASE_URLS["openrouter"]
    )


def model_supports_vision(provider: str, model: str) -> bool:
    normalized_provider = normalize_llm_provider(provider)
    normalized_model = str(model or "").strip().lower()
    if not normalized_model:
        return False

    if normalized_provider == "anthropic":
        return "claude-3" in normalized_model or "claude-sonnet-4" in normalized_model

    if normalized_provider in {"openrouter", "openai"}:
        vision_markers = (
            "gpt-4o",
            "gpt-4.1",
            "gemini",
            "claude-3",
            "claude-sonnet-4",
            "qwen-vl",
            "llava",
            "pixtral",
            "vision",
        )
        return any(marker in normalized_model for marker in vision_markers)

    if normalized_provider == "ollama":
        return any(marker in normalized_model for marker in ("llava", "vision", "moondream", "minicpm-v"))

    return False


@lru_cache(maxsize=1)
def _get_merged_catalogs() -> dict[str, dict[str, Any]]:
    catalogs = copy.deepcopy(_MODEL_CATALOG)

    for provider in ("openrouter", "openai"):
        bundled_catalog = provider_catalog_from_registry(provider)
        if bundled_catalog.get("main_models"):
            catalogs[provider] = {
                **catalogs.get(provider, {}),
                **bundled_catalog,
            }

    for p in SUPPORTED_LLM_PROVIDERS:
        if p not in catalogs:
            catalogs[p] = {
                "main_models": [],
                "lite_models": [],
                "default_main_model": "",
                "default_lite_model": "",
                "models": [],
            }
        elif "models" not in catalogs[p]:
            catalogs[p]["models"] = []

    return catalogs


def provider_model_catalog(provider: str) -> dict[str, Any]:
    normalized = normalize_llm_provider(provider)
    catalogs = _get_merged_catalogs()
    catalog = catalogs.get(normalized, catalogs["openrouter"])
    return {
        "main_models": list(catalog["main_models"]),
        "lite_models": list(catalog["lite_models"]),
        "default_main_model": str(catalog["default_main_model"]),
        "default_lite_model": str(catalog["default_lite_model"]),
        "models": list(catalog.get("models", [])),
    }


def all_provider_model_catalogs() -> dict[str, dict[str, Any]]:
    catalogs = _get_merged_catalogs()
    return {
        provider: {
            "main_models": list(
                catalogs.get(provider, catalogs["openrouter"])["main_models"]
            ),
            "lite_models": list(
                catalogs.get(provider, catalogs["openrouter"])["lite_models"]
            ),
            "default_main_model": str(
                catalogs.get(provider, catalogs["openrouter"])["default_main_model"]
            ),
            "default_lite_model": str(
                catalogs.get(provider, catalogs["openrouter"])["default_lite_model"]
            ),
            "models": list(catalogs.get(provider, catalogs["openrouter"]).get("models", [])),
        }
        for provider in SUPPORTED_LLM_PROVIDERS
    }
