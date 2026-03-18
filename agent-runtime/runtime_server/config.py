from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PhoenixConfig:
    enabled: bool = False
    project: str = "inquira-agent"
    endpoint: str = "http://127.0.0.1:6006/v1/traces"


@dataclass(frozen=True)
class AgentServiceConfig:
    host: str = "127.0.0.1"
    port: int = 8123
    api_major: int = 1
    auth_mode: str = "shared_secret"
    shared_secret: str = ""
    default_agent: str = "agent_v2"
    available_agents: tuple[str, ...] = ("agent_v1", "agent_v2")
    phoenix: PhoenixConfig = PhoenixConfig()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _load_toml_data() -> dict[str, Any]:
    cfg_path = os.getenv("INQUIRA_TOML_PATH")
    if cfg_path:
        path = Path(cfg_path)
    else:
        path = Path(__file__).resolve().parents[2] / "inquira.toml"

    if not path.exists():
        return {}

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _load_available_agents(runtime_root: Path) -> tuple[str, ...]:
    langgraph_path = runtime_root / "langgraph.json"
    if not langgraph_path.exists():
        return ("agent_v2",)
    try:
        data = json.loads(langgraph_path.read_text(encoding="utf-8"))
    except Exception:
        return ("agent_v2",)
    graphs = data.get("graphs") if isinstance(data, dict) else {}
    if not isinstance(graphs, dict):
        return ("agent_v2",)
    names = tuple(str(k).strip() for k in graphs.keys() if str(k).strip())
    return names or ("agent_v2",)


def load_agent_service_config() -> AgentServiceConfig:
    data = _load_toml_data()
    raw_section = data.get("agent_service", {})
    section = raw_section if isinstance(raw_section, dict) else {}
    raw_auth = section.get("auth", {})
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    raw_phoenix = section.get("phoenix", {})
    phoenix = raw_phoenix if isinstance(raw_phoenix, dict) else {}

    host = str(os.getenv("INQUIRA_AGENT_HOST") or section.get("host") or "127.0.0.1").strip() or "127.0.0.1"
    port = max(1, _as_int(os.getenv("INQUIRA_AGENT_PORT") or section.get("port") or 8123, 8123))
    api_major = max(1, _as_int(section.get("api_major") or section.get("expected_api_major") or 1, 1))
    auth_mode = str(auth.get("mode") or "shared_secret").strip().lower() or "shared_secret"
    shared_secret = str(os.getenv("INQUIRA_AGENT_SHARED_SECRET") or auth.get("shared_secret") or "").strip()
    default_agent = str(section.get("default_agent") or "agent_v2").strip() or "agent_v2"

    runtime_root = Path(__file__).resolve().parents[1]
    available_agents = _load_available_agents(runtime_root)
    if default_agent not in available_agents:
        default_agent = available_agents[0]

    phx_enabled = _as_bool(os.getenv("INQUIRA_AGENT_PHOENIX_ENABLED"), _as_bool(phoenix.get("enabled"), False))
    phx_project = str(os.getenv("INQUIRA_AGENT_PHOENIX_PROJECT") or phoenix.get("project") or "inquira-agent").strip() or "inquira-agent"
    phx_endpoint = str(os.getenv("INQUIRA_AGENT_PHOENIX_ENDPOINT") or phoenix.get("endpoint") or "http://127.0.0.1:6006/v1/traces").strip()

    return AgentServiceConfig(
        host=host,
        port=port,
        api_major=api_major,
        auth_mode=auth_mode,
        shared_secret=shared_secret,
        default_agent=default_agent,
        available_agents=available_agents,
        phoenix=PhoenixConfig(enabled=phx_enabled, project=phx_project, endpoint=phx_endpoint),
    )
