import os
import tomllib
from pathlib import Path
from typing import Any, Callable

from ..core.logger import logprint


_tracing_initialized = False


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _load_register() -> Callable[..., Any]:
    from phoenix.otel import register

    return register


def _load_toml_settings() -> dict[str, Any]:
    cfg_path = os.getenv("INQUIRA_TOML_PATH")
    if cfg_path:
        path = Path(cfg_path)
    else:
        # repo root / inquira.toml
        path = Path(__file__).resolve().parents[3] / "inquira.toml"

    if not path.exists():
        return {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    # Supported sections:
    # [backend.phoenix]
    # [phoenix]
    backend = data.get("backend", {})
    if isinstance(backend, dict):
        phx = backend.get("phoenix", {})
        if isinstance(phx, dict):
            return phx

    phx = data.get("phoenix", {})
    if isinstance(phx, dict):
        return phx

    return {}


def init_phoenix_tracing() -> bool:
    """
    Minimal Phoenix setup following Arize docs:
    - phoenix.otel.register(...)
    - auto_instrument=True for LangChain/LangGraph tracing
    """
    global _tracing_initialized

    if _tracing_initialized:
        return True

    toml_settings = _load_toml_settings()
    enabled_env = os.getenv("INQUIRA_PHOENIX_ENABLED")
    enabled_cfg = toml_settings.get("enabled")
    enabled = _is_enabled(enabled_env) if enabled_env is not None else bool(enabled_cfg)

    if not enabled:
        return False

    try:
        register = _load_register()
    except Exception as e:
        logprint(
            f"Phoenix tracing requested but phoenix is not available: {e}",
            level="warning",
        )
        return False

    project_name = os.getenv(
        "INQUIRA_PHOENIX_PROJECT", str(toml_settings.get("project", "inquira-dev"))
    )
    endpoint = os.getenv(
        "INQUIRA_PHOENIX_ENDPOINT", str(toml_settings.get("endpoint", ""))
    ).strip()

    kwargs: dict[str, Any] = {
        "project_name": project_name,
        "auto_instrument": True,
    }
    if endpoint:
        kwargs["endpoint"] = endpoint

    try:
        register(**kwargs)
        _tracing_initialized = True
        logprint(
            "Phoenix tracing enabled",
            level="info",
            project_name=project_name,
            endpoint=endpoint or "default",
        )
        return True
    except Exception as e:
        logprint(f"Failed to initialize Phoenix tracing: {e}", level="error")
        return False
