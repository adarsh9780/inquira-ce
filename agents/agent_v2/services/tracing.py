"""Agent wrapper for shared Phoenix tracing bootstrap."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable

_logger = logging.getLogger(__name__)


def _log(message: str, level: str = "info", **kwargs: Any) -> None:
    details = ", ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    rendered = f"{message} ({details})" if details else message
    if level == "error":
        _logger.error(rendered)
    elif level == "warning":
        _logger.warning(rendered)
    else:
        _logger.info(rendered)


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).parent.parent.parent
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


def _load_shared_init() -> Callable[..., bool]:
    _ensure_repo_root_on_path()
    from shared.observability.phoenix import init_phoenix_tracing as shared_init

    return shared_init


def _load_shared_reset() -> Callable[[], None]:
    _ensure_repo_root_on_path()
    from shared.observability.phoenix import reset_phoenix_tracing_state as shared_reset

    return shared_reset


def init_phoenix_tracing() -> bool:
    shared_init = _load_shared_init()
    return shared_init(
        section_path=("agent_service", "phoenix"),
        enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
        project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
        endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
        default_project="inquira-agent",
        log=_log,
    )


def reset_phoenix_tracing_state() -> None:
    shared_reset = _load_shared_reset()
    shared_reset()
