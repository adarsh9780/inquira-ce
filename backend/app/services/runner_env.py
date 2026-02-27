"""Runner virtualenv helpers for kernel dependency management."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.execution_config import ExecutionRuntimeConfig


@dataclass(frozen=True)
class RunnerInstallResult:
    installer: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def resolve_runner_python(config: ExecutionRuntimeConfig) -> str:
    """Return runner Python executable path or raise a descriptive error."""
    runner_python = (config.runner_python_executable or "").strip()
    if not runner_python:
        raise RuntimeError(
            "INQUIRA_RUNNER_PYTHON is required for provider 'local_jupyter'."
        )
    path = Path(runner_python).expanduser()
    if not path.exists():
        raise RuntimeError(f"Runner Python executable does not exist: {path}")
    return str(path)


def ensure_runner_kernel_dependencies(config: ExecutionRuntimeConfig) -> None:
    """Ensure the runner virtualenv has kernel/runtime dependencies installed."""
    runner_python = resolve_runner_python(config)
    required_packages = _build_required_packages(config)
    _install_with_uv_or_pip(
        runner_python,
        required_packages,
        index_url=config.runner_index_url,
    )


def _build_required_packages(config: ExecutionRuntimeConfig) -> list[str]:
    defaults = ["ipykernel", "narwhals", "duckdb", "pandas", "plotly"]
    merged: list[str] = []
    seen: set[str] = set()

    for package in [*defaults, *config.runner_packages]:
        name = str(package).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(name)
    return merged


def install_runner_package(
    config: ExecutionRuntimeConfig,
    package_spec: str,
    index_url: str | None = None,
) -> RunnerInstallResult:
    runner_python = resolve_runner_python(config)
    effective_index_url = (index_url or "").strip() or config.runner_index_url
    return _install_with_uv_or_pip(
        runner_python,
        [package_spec],
        index_url=effective_index_url,
    )


def _install_with_uv_or_pip(
    runner_python: str,
    packages: list[str],
    index_url: str | None = None,
) -> RunnerInstallResult:
    uv_cmd = ["uv", "pip", "install", "--python", runner_python]
    if index_url:
        uv_cmd.extend(["--index-url", index_url])
    uv_cmd.extend(packages)
    uv_proc = subprocess.run(uv_cmd, capture_output=True, text=True)
    if uv_proc.returncode == 0:
        return RunnerInstallResult(
            installer="uv",
            command=uv_cmd,
            returncode=uv_proc.returncode,
            stdout=uv_proc.stdout or "",
            stderr=uv_proc.stderr or "",
        )

    pip_cmd = [runner_python, "-m", "pip", "install"]
    if index_url:
        pip_cmd.extend(["--index-url", index_url])
    pip_cmd.extend(packages)
    pip_proc = subprocess.run(pip_cmd, capture_output=True, text=True)
    if pip_proc.returncode == 0:
        return RunnerInstallResult(
            installer="pip",
            command=pip_cmd,
            returncode=pip_proc.returncode,
            stdout=pip_proc.stdout or "",
            stderr=pip_proc.stderr or "",
        )

    uv_err = (uv_proc.stderr or uv_proc.stdout or "").strip()
    pip_err = (pip_proc.stderr or pip_proc.stdout or "").strip()
    raise RuntimeError(
        "Failed to install runner kernel dependencies. "
        f"uv error: {uv_err or '<none>'}; pip error: {pip_err or '<none>'}"
    )
