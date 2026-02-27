"""Execution runtime configuration loaded from env and ``inquira.toml``."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunnerPolicyConfig:
    """Execution policy values shared by runtime providers."""

    timeout_seconds: int = 60
    memory_limit_mb: int = 512
    max_output_kb: int = 512
    blocked_imports: list[str] = field(default_factory=list)
    blocked_builtins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionRuntimeConfig:
    """Runtime execution provider and runner environment settings."""

    provider: str = "local_jupyter"
    runner_python_executable: str | None = None
    runner_venv_name: str = ".runner-venv"
    runner_packages: list[str] = field(default_factory=list)
    runner_index_url: str | None = None
    runner_package_allowlist: list[str] = field(default_factory=list)
    runner_package_denylist: list[str] = field(default_factory=list)
    runner_install_max_packages_per_request: int = 1
    kernel_idle_minutes: int = 30
    runner_policy: RunnerPolicyConfig = field(default_factory=RunnerPolicyConfig)


def _as_int(value: Any, default: int) -> int:
    """Return ``value`` coerced to ``int`` or ``default`` when invalid."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str_list(value: Any) -> list[str]:
    """Return a list of non-empty strings from a TOML array value."""

    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _load_toml_data() -> dict[str, Any]:
    """Load ``inquira.toml`` and return a mapping object."""

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
def load_execution_runtime_config() -> ExecutionRuntimeConfig:
    """Build cached runtime config from environment and TOML settings."""

    data = _load_toml_data()
    execution = data.get("execution", {})
    if not isinstance(execution, dict):
        execution = {}

    runner = execution.get("runner", {})
    if not isinstance(runner, dict):
        runner = {}

    provider = str(
        os.getenv("INQUIRA_EXECUTION_PROVIDER")
        or execution.get("provider")
        or "local_jupyter"
    ).strip()

    runner_python = (
        os.getenv("INQUIRA_RUNNER_PYTHON")
        or runner.get("python-executable")
        or None
    )
    runner_venv_name = str(
        runner.get("venv-name")
        or ".runner-venv"
    ).strip() or ".runner-venv"
    runner_packages = _as_str_list(runner.get("packages"))
    runner_index_url = str(runner.get("index-url") or "").strip() or None
    runner_package_allowlist = _as_str_list(runner.get("package-allowlist"))
    runner_package_denylist = _as_str_list(runner.get("package-denylist"))
    runner_install_max_packages_per_request = _as_int(
        runner.get("install-max-packages-per-request", 1),
        1,
    )
    kernel_idle_minutes = _as_int(runner.get("kernel-idle-minutes", 30), 30)

    policy = RunnerPolicyConfig(
        timeout_seconds=_as_int(runner.get("timeout-seconds", 60), 60),
        memory_limit_mb=_as_int(runner.get("memory-limit-mb", 512), 512),
        max_output_kb=_as_int(runner.get("max-output-kb", 512), 512),
        blocked_imports=_as_str_list(runner.get("blocked-imports")),
        blocked_builtins=_as_str_list(runner.get("blocked-builtins")),
    )
    return ExecutionRuntimeConfig(
        provider=provider,
        runner_python_executable=str(runner_python) if runner_python else None,
        runner_venv_name=runner_venv_name,
        runner_packages=runner_packages,
        runner_index_url=runner_index_url,
        runner_package_allowlist=runner_package_allowlist,
        runner_package_denylist=runner_package_denylist,
        runner_install_max_packages_per_request=max(1, runner_install_max_packages_per_request),
        kernel_idle_minutes=max(1, kernel_idle_minutes),
        runner_policy=policy,
    )
