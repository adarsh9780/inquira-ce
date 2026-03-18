"""Agent v2 runtime configuration loader."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


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


@dataclass(frozen=True)
class AgentRuntimeConfig:
    max_tool_calls: int = 5
    max_code_executions: int = 3
    turn_timeout: int = 120
    intervention_timeout_seconds: int = 60
    bash_allowed_commands: tuple[str, ...] = ("rg", "grep", "wc", "head", "tail", "ls", "cat", "find")
    bash_sandbox: str = "."
    bash_max_output_chars: int = 2000
    memory_max_recent_messages: int = 10
    memory_max_summary_tokens: int = 500


@lru_cache(maxsize=1)
def load_agent_runtime_config() -> AgentRuntimeConfig:
    data = _load_toml_data()
    raw_agent = data.get("agent", {})
    agent = raw_agent if isinstance(raw_agent, dict) else {}
    raw_bash = agent.get("bash", {})
    bash = raw_bash if isinstance(raw_bash, dict) else {}
    raw_memory = agent.get("memory", {})
    memory = raw_memory if isinstance(raw_memory, dict) else {}
    raw_intervention = agent.get("intervention", {})
    intervention = raw_intervention if isinstance(raw_intervention, dict) else {}

    return AgentRuntimeConfig(
        max_tool_calls=max(1, _as_int(agent.get("max-tool-calls", 5), 5)),
        max_code_executions=max(1, _as_int(agent.get("max-code-executions", 3), 3)),
        turn_timeout=max(10, _as_int(agent.get("turn-timeout", 120), 120)),
        intervention_timeout_seconds=max(
            5,
            _as_int(intervention.get("timeout-seconds", 60), 60),
        ),
        bash_allowed_commands=tuple(
            _as_str_list(bash.get("allowed-commands"))
            or ["rg", "grep", "wc", "head", "tail", "ls", "cat", "find"]
        ),
        bash_sandbox=str(bash.get("sandbox") or ".").strip() or ".",
        bash_max_output_chars=max(200, _as_int(bash.get("max-output-chars", 2000), 2000)),
        memory_max_recent_messages=max(1, _as_int(memory.get("max-recent-messages", 10), 10)),
        memory_max_summary_tokens=max(64, _as_int(memory.get("max-summary-tokens", 500), 500)),
    )
