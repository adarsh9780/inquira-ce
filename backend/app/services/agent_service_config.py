"""Agent service runtime configuration for backend->agent API calls."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentServiceConfig:
    host: str = "127.0.0.1"
    port: int = 8123
    expected_api_major: int = 1
    startup_timeout_sec: int = 45
    auth_mode: str = "shared_secret"
    shared_secret: str = ""

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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


@lru_cache(maxsize=1)
def load_agent_service_config() -> AgentServiceConfig:
    data = _load_toml_data()
    raw = data.get("agent_service", {})
    section = raw if isinstance(raw, dict) else {}
    raw_auth = section.get("auth", {})
    auth = raw_auth if isinstance(raw_auth, dict) else {}

    host = str(os.getenv("INQUIRA_AGENT_HOST") or section.get("host") or "127.0.0.1").strip() or "127.0.0.1"
    port = max(1, _as_int(os.getenv("INQUIRA_AGENT_PORT") or section.get("port") or 8123, 8123))
    expected_api_major = max(
        1,
        _as_int(section.get("expected_api_major") or section.get("api_major") or 1, 1),
    )
    startup_timeout_sec = max(3, _as_int(section.get("startup_timeout_sec") or 45, 45))
    auth_mode = str(auth.get("mode") or "shared_secret").strip().lower() or "shared_secret"
    shared_secret = str(
        os.getenv("INQUIRA_AGENT_SHARED_SECRET") or auth.get("shared_secret") or ""
    ).strip()

    return AgentServiceConfig(
        host=host,
        port=port,
        expected_api_major=expected_api_major,
        startup_timeout_sec=startup_timeout_sec,
        auth_mode=auth_mode,
        shared_secret=shared_secret,
    )
