"""Shared Phoenix tracing bootstrap used by backend and agent runtimes."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any, Callable

_initialized_keys: set[str] = set()


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _default_toml_path() -> Path:
    cfg_path = os.getenv("INQUIRA_TOML_PATH")
    if cfg_path:
        return Path(cfg_path)
    return Path(__file__).resolve().parents[2] / "inquira.toml"


def _load_toml_section(section_path: tuple[str, ...]) -> dict[str, Any]:
    path = _default_toml_path()
    if not path.exists():
        return {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    current: Any = data
    for key in section_path:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _load_register() -> Callable[..., Any]:
    from phoenix.otel import register

    return register


def _logger_noop(message: str, level: str = "info", **kwargs: Any) -> None:
    _ = (message, level, kwargs)


def reset_phoenix_tracing_state() -> None:
    """Reset initialization guards for tests."""
    _initialized_keys.clear()


def init_phoenix_tracing(
    *,
    section_path: tuple[str, ...],
    enabled_env: str,
    project_env: str,
    endpoint_env: str,
    default_project: str,
    log: Callable[..., None] | None = None,
    load_register: Callable[[], Callable[..., Any]] | None = None,
) -> bool:
    """Initialize Phoenix tracing for a specific process/section."""

    logger = log or _logger_noop
    section_key = ".".join(section_path)
    if section_key in _initialized_keys:
        return True

    toml_settings = _load_toml_section(section_path)
    enabled_raw = os.getenv(enabled_env)
    enabled = _is_enabled(enabled_raw) if enabled_raw is not None else bool(toml_settings.get("enabled"))
    if not enabled:
        return False

    resolver = load_register or _load_register
    try:
        register = resolver()
    except Exception as exc:
        logger(
            f"Phoenix tracing requested but phoenix is not available: {exc}",
            level="warning",
            section=section_key,
        )
        return False

    project_name = os.getenv(project_env, str(toml_settings.get("project", default_project)))
    endpoint = os.getenv(endpoint_env, str(toml_settings.get("endpoint", ""))).strip()

    kwargs: dict[str, Any] = {
        "project_name": project_name,
        "auto_instrument": True,
    }
    if endpoint:
        kwargs["endpoint"] = endpoint

    try:
        register(**kwargs)
        _initialized_keys.add(section_key)
        logger(
            "Phoenix tracing enabled",
            level="info",
            section=section_key,
            project_name=project_name,
            endpoint=endpoint or "default",
        )
        return True
    except Exception as exc:
        logger(
            f"Failed to initialize Phoenix tracing: {exc}",
            level="error",
            section=section_key,
        )
        return False

