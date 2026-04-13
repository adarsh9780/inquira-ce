"""Bundled LLM model registry helpers used by v1 preferences and refresh flows."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LLM_PROVIDERS: tuple[str, ...] = (
    "openrouter",
    "openai",
    "anthropic",
    "ollama",
)

_RECOMMENDED_FOR_ALLOWED = {"main", "lite", "both"}
_TAGS_ALLOWED = {"recommended", "extended"}
_LITE_HINTS: tuple[str, ...] = (
    "nano",
    "mini",
    "haiku",
    "lite",
    "small",
    ":3b",
    ":2b",
    "flash-lite",
    "flash",
)


def _normalize_provider(provider: Any) -> str:
    value = str(provider or "").strip().lower()
    if value in SUPPORTED_LLM_PROVIDERS:
        return value
    return "openrouter"


@lru_cache(maxsize=1)
def _models_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "models.json"


@lru_cache(maxsize=1)
def load_bundled_model_registry() -> dict[str, Any]:
    path = _models_file_path()
    if not path.exists():
        return {"last_updated": "", "models": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"last_updated": "", "models": []}

    if not isinstance(payload, dict):
        return {"last_updated": "", "models": []}

    raw_models = payload.get("models")
    if not isinstance(raw_models, list):
        raw_models = []

    cleaned_models = [
        _normalize_model_entry(item)
        for item in raw_models
        if isinstance(item, dict)
    ]
    cleaned_models = [item for item in cleaned_models if item is not None]

    return {
        "last_updated": str(payload.get("last_updated") or "").strip(),
        "models": cleaned_models,
    }


def clear_model_registry_cache() -> None:
    load_bundled_model_registry.cache_clear()


def provider_registry_entries(provider: str) -> list[dict[str, Any]]:
    normalized = _normalize_provider(provider)
    models = load_bundled_model_registry().get("models", [])
    if not isinstance(models, list):
        return []
    return [
        dict(item)
        for item in models
        if isinstance(item, dict) and _normalize_provider(item.get("provider", "")) == normalized
    ]


def provider_catalog_from_registry(provider: str) -> dict[str, Any]:
    entries = provider_registry_entries(provider)

    main_models: list[str] = []
    lite_models: list[str] = []

    for entry in entries:
        model_id = str(entry.get("id") or "").strip()
        if not model_id:
            continue

        recommended_for = _normalize_recommended_for(entry.get("recommended_for"))
        if "main" in recommended_for or "both" in recommended_for:
            main_models.append(model_id)
        if "lite" in recommended_for or "both" in recommended_for:
            lite_models.append(model_id)

    if not main_models and entries:
        main_models = [str(entries[0].get("id") or "").strip()]
    if not lite_models:
        # Keep fallback ergonomic when no lite entries are tagged.
        lite_models = list(main_models[:1]) if main_models else []

    return {
        "main_models": _unique_models(main_models),
        "lite_models": _unique_models(lite_models),
        "default_main_model": main_models[0] if main_models else "",
        "default_lite_model": lite_models[0] if lite_models else "",
        "source": "bundled",
        "models": entries,
    }


def merge_refreshed_model_metadata(
    provider: str,
    existing_entries: list[dict[str, Any]] | None,
    refreshed_main_models: list[str],
    refreshed_lite_models: list[str],
) -> list[dict[str, Any]]:
    normalized_provider = _normalize_provider(provider)

    existing = [
        _normalize_model_entry(item)
        for item in (existing_entries or [])
        if isinstance(item, dict)
    ]
    existing = [item for item in existing if item is not None]

    existing_by_id = {
        str(item.get("id") or "").strip(): dict(item)
        for item in existing
        if str(item.get("id") or "").strip()
    }

    ordered_ids: list[str] = [
        str(item.get("id") or "").strip()
        for item in existing
        if str(item.get("id") or "").strip()
    ]

    main_set = set(_clean_model_id_list(refreshed_main_models))
    lite_set = set(_clean_model_id_list(refreshed_lite_models))

    for model_id in _clean_model_id_list([*refreshed_main_models, *refreshed_lite_models]):
        if model_id in existing_by_id:
            continue

        recommended_for = _recommended_for_from_membership(model_id, main_set, lite_set)
        extended_entry = _normalize_model_entry(
            {
                "id": model_id,
                "display_name": _display_name_from_model_id(model_id),
                "provider": normalized_provider,
                "context_window": 0,
                "recommended_for": recommended_for,
                "tags": ["extended"],
            }
        )
        if extended_entry is None:
            continue
        existing_by_id[model_id] = extended_entry
        ordered_ids.append(model_id)

    merged: list[dict[str, Any]] = []
    for model_id in ordered_ids:
        item = existing_by_id.get(model_id)
        if not item:
            continue
        merged.append(dict(item))

    return merged


def _normalize_model_entry(raw: dict[str, Any]) -> dict[str, Any] | None:
    model_id = str(raw.get("id") or "").strip()
    if not model_id:
        return None

    provider = _normalize_provider(raw.get("provider", "openrouter"))
    if provider == "ollama":
        # Ollama models are always fetched live and never persisted in bundled registry metadata.
        return None

    display_name = str(raw.get("display_name") or "").strip() or _display_name_from_model_id(model_id)

    context_window_raw = raw.get("context_window")
    try:
        context_window = int(context_window_raw)
    except Exception:  # noqa: BLE001
        context_window = 0
    if context_window < 0:
        context_window = 0

    recommended_for = _normalize_recommended_for(raw.get("recommended_for"))
    tags = _normalize_tags(raw.get("tags"))

    return {
        "id": model_id,
        "display_name": display_name,
        "provider": provider,
        "context_window": context_window,
        "recommended_for": recommended_for,
        "tags": tags,
    }


def _clean_model_id_list(values: list[Any]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def _normalize_recommended_for(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw_list = [raw]
    elif isinstance(raw, list):
        raw_list = raw
    else:
        raw_list = []

    cleaned: list[str] = []
    for item in raw_list:
        value = str(item or "").strip().lower()
        if value in _RECOMMENDED_FOR_ALLOWED and value not in cleaned:
            cleaned.append(value)

    if not cleaned:
        return ["main"]

    if "both" in cleaned:
        return ["both"]

    return cleaned


def _normalize_tags(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw_list = [raw]
    elif isinstance(raw, list):
        raw_list = raw
    else:
        raw_list = []

    cleaned: list[str] = []
    for item in raw_list:
        value = str(item or "").strip().lower()
        if value in _TAGS_ALLOWED and value not in cleaned:
            cleaned.append(value)

    if not cleaned:
        return ["recommended"]

    return cleaned


def _recommended_for_from_membership(model_id: str, main_set: set[str], lite_set: set[str]) -> list[str]:
    in_main = model_id in main_set
    in_lite = model_id in lite_set
    if in_main and in_lite:
        return ["both"]
    if in_lite:
        return ["lite"]
    if in_main:
        return ["main"]

    lowered = model_id.lower()
    if any(hint in lowered for hint in _LITE_HINTS):
        return ["lite"]
    return ["main"]


def _display_name_from_model_id(model_id: str) -> str:
    base = str(model_id or "").strip()
    if not base:
        return "Unknown Model"

    if "/" in base:
        base = base.split("/", 1)[1]

    normalized = base.replace("_", " ").replace("-", " ").strip()
    if not normalized:
        return model_id

    return " ".join(segment.capitalize() for segment in normalized.split())


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
