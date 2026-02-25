"""LLM runtime configuration loaded from env and inquira.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LlmRuntimeConfig:
    provider: str = "openrouter"
    base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "google/gemini-2.5-flash"
    lite_model: str = "google/gemini-2.5-flash-lite"
    default_max_tokens: int = 4096
    schema_max_tokens: int = 2048
    code_generation_max_tokens: int = 4096
    supported_models: tuple[str, ...] = (
        "google/gemini-3-flash-preview",
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "openrouter/free",
    )


_MODEL_ALIASES: dict[str, str] = {
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-flash-lite": "google/gemini-2.5-flash-lite",
    "openrouter/free": "openrouter/free",
}


def normalize_model_id(model: str) -> str:
    raw = (model or "").strip()
    if not raw:
        return raw
    return _MODEL_ALIASES.get(raw.lower(), raw)


def _validate_toml_model_id(value: Any, field_name: str) -> None:
    raw = str(value or "").strip()
    if not raw:
        return
    normalized = normalize_model_id(raw)
    if normalized != raw:
        raise ValueError(
            f"[llm].{field_name} must use the full model ID '{normalized}', not shorthand '{raw}'."
        )


def _validate_and_normalize_model_list(raw_models: Any, field_name: str) -> list[str]:
    if raw_models is None:
        return []
    values: list[str]
    if isinstance(raw_models, str):
        values = [item.strip() for item in raw_models.split(",")]
    elif isinstance(raw_models, list):
        values = [str(item).strip() for item in raw_models]
    else:
        raise ValueError(f"{field_name} must be a list of model IDs or comma-separated string.")

    normalized_unique: list[str] = []
    for item in values:
        if not item:
            continue
        normalized = normalize_model_id(item)
        if normalized != item:
            raise ValueError(
                f"{field_name} must use the full model ID '{normalized}', not shorthand '{item}'."
            )
        if normalized not in normalized_unique:
            normalized_unique.append(normalized)
    return normalized_unique


def _load_toml_data() -> dict[str, Any]:
    cfg_path = os.getenv("INQUIRA_TOML_PATH")
    if cfg_path:
        path = Path(cfg_path)
    else:
        path = Path(__file__).resolve().parents[3] / "inquira.toml"

    if not path.exists():
        return {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _parse_positive_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a positive integer.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return parsed


@lru_cache(maxsize=1)
def load_llm_runtime_config() -> LlmRuntimeConfig:
    data = _load_toml_data()
    llm = data.get("llm", {})
    if not isinstance(llm, dict):
        llm = {}
    llm_limits = llm.get("limits", {})
    if not isinstance(llm_limits, dict):
        llm_limits = {}

    _validate_toml_model_id(llm.get("default-model"), "default-model")
    _validate_toml_model_id(llm.get("lite-model"), "lite-model")

    provider = str(
        os.getenv("INQUIRA_LLM_PROVIDER") or llm.get("provider") or "openrouter"
    ).strip()
    base_url = str(
        os.getenv("INQUIRA_LLM_BASE_URL")
        or llm.get("base-url")
        or "https://openrouter.ai/api/v1"
    ).strip()
    default_model = str(
        os.getenv("INQUIRA_LLM_DEFAULT_MODEL")
        or llm.get("default-model")
        or "google/gemini-2.5-flash"
    ).strip()
    lite_model = str(
        os.getenv("INQUIRA_LLM_LITE_MODEL")
        or llm.get("lite-model")
        or "google/gemini-2.5-flash-lite"
    ).strip()
    supported_models_raw = os.getenv("INQUIRA_LLM_MODELS")
    if supported_models_raw is None:
        supported_models_raw = llm.get("models")
    supported_models = _validate_and_normalize_model_list(
        supported_models_raw, "[llm].models"
    )
    if not supported_models:
        supported_models = list(LlmRuntimeConfig.supported_models)

    default_max_tokens_raw: Any = os.getenv("INQUIRA_LLM_DEFAULT_MAX_TOKENS")
    if default_max_tokens_raw is None:
        default_max_tokens_raw = llm_limits.get("default")
    if default_max_tokens_raw is None:
        default_max_tokens_raw = llm.get("default-max-tokens")
    if default_max_tokens_raw is None:
        default_max_tokens_raw = 4096
    schema_max_tokens_raw: Any = os.getenv("INQUIRA_LLM_SCHEMA_MAX_TOKENS")
    if schema_max_tokens_raw is None:
        schema_max_tokens_raw = llm_limits.get("schema")
    if schema_max_tokens_raw is None:
        schema_max_tokens_raw = 2048
    code_generation_max_tokens_raw: Any = os.getenv("INQUIRA_LLM_CODE_MAX_TOKENS")
    if code_generation_max_tokens_raw is None:
        code_generation_max_tokens_raw = llm_limits.get("code_generation")
    if code_generation_max_tokens_raw is None:
        code_generation_max_tokens_raw = 4096

    default_max_tokens = _parse_positive_int(default_max_tokens_raw, "[llm.limits].default")
    schema_max_tokens = _parse_positive_int(schema_max_tokens_raw, "[llm.limits].schema")
    code_generation_max_tokens = _parse_positive_int(
        code_generation_max_tokens_raw, "[llm.limits].code_generation"
    )
    normalized_default_model = normalize_model_id(default_model)
    normalized_lite_model = normalize_model_id(lite_model)
    if normalized_default_model and normalized_default_model not in supported_models:
        supported_models.append(normalized_default_model)
    if normalized_lite_model and normalized_lite_model not in supported_models:
        supported_models.append(normalized_lite_model)

    return LlmRuntimeConfig(
        provider=provider.lower(),
        base_url=base_url,
        default_model=normalized_default_model,
        lite_model=normalized_lite_model,
        default_max_tokens=default_max_tokens,
        schema_max_tokens=schema_max_tokens,
        code_generation_max_tokens=code_generation_max_tokens,
        supported_models=tuple(supported_models),
    )
