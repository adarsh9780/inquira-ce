"""Execution runtime configuration loaded from env and inquira.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunnerPolicyConfig:
    timeout_seconds: int = 60
    memory_limit_mb: int = 512
    max_output_kb: int = 512
    blocked_imports: list[str] = field(default_factory=list)
    blocked_builtins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionRuntimeConfig:
    provider: str = "local_subprocess"
    runner_python_executable: str | None = None
    runner_project_path: str | None = None
    safe_py_runner_source: str = "auto"
    safe_py_runner_pypi: str = "safe-py-runner"
    safe_py_runner_github: str = "git+https://github.com/adarsh9780/safe-py-runner.git"
    safe_py_runner_local_path: str | None = None
    runner_policy: RunnerPolicyConfig = field(default_factory=RunnerPolicyConfig)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


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
def load_execution_runtime_config() -> ExecutionRuntimeConfig:
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
        or "local_subprocess"
    ).strip()

    runner_python = (
        os.getenv("INQUIRA_RUNNER_PYTHON")
        or runner.get("python-executable")
        or None
    )
    runner_project_path = (
        os.getenv("INQUIRA_SAFE_PY_RUNNER_PROJECT_PATH")
        or runner.get("project-path")
        or None
    )
    safe_py_runner_source = str(
        os.getenv("INQUIRA_SAFE_PY_RUNNER_SOURCE")
        or runner.get("safe-py-runner-source")
        or "auto"
    ).strip()
    safe_py_runner_pypi = str(
        os.getenv("INQUIRA_SAFE_PY_RUNNER_PYPI")
        or runner.get("safe-py-runner-pypi")
        or "safe-py-runner"
    ).strip()
    safe_py_runner_github = str(
        os.getenv("INQUIRA_SAFE_PY_RUNNER_GITHUB")
        or runner.get("safe-py-runner-github")
        or "git+https://github.com/adarsh9780/safe-py-runner.git"
    ).strip()
    safe_py_runner_local_path = (
        os.getenv("INQUIRA_SAFE_PY_RUNNER_LOCAL_PATH")
        or runner.get("safe-py-runner-local-path")
        or runner_project_path
        or None
    )

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
        runner_project_path=str(runner_project_path) if runner_project_path else None,
        safe_py_runner_source=safe_py_runner_source.lower(),
        safe_py_runner_pypi=safe_py_runner_pypi,
        safe_py_runner_github=safe_py_runner_github,
        safe_py_runner_local_path=(
            str(safe_py_runner_local_path) if safe_py_runner_local_path else None
        ),
        runner_policy=policy,
    )
