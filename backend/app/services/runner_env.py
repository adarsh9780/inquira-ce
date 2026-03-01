"""Runner virtualenv helpers for kernel dependency management."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
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


@dataclass(frozen=True)
class RunnerEnvironmentStatus:
    venv_path: str
    python_executable: str
    created: bool
    packages_installed: bool
    packages: list[str]


def resolve_workspace_runner_venv(workspace_duckdb_path: str) -> Path:
    """Return workspace-local runner venv path."""
    workspace_root = Path(workspace_duckdb_path).expanduser().resolve().parent
    return workspace_root / ".venv"


def resolve_runner_python(
    config: ExecutionRuntimeConfig,
    workspace_duckdb_path: str | None = None,
) -> str:
    """Return runner Python executable path or raise a descriptive error."""
    if workspace_duckdb_path:
        workspace_python = _python_bin_from_venv(resolve_workspace_runner_venv(workspace_duckdb_path))
        if workspace_python.exists():
            return str(workspace_python)

    runner_python = (config.runner_python_executable or "").strip()
    if not runner_python:
        raise RuntimeError(
            "Workspace runner python is not initialized. Bootstrap the workspace runtime first."
        )
    path = Path(runner_python).expanduser()
    if not path.exists():
        raise RuntimeError(f"Runner Python executable does not exist: {path}")
    return str(path)


def ensure_runner_kernel_dependencies(
    config: ExecutionRuntimeConfig,
    workspace_duckdb_path: str,
) -> RunnerEnvironmentStatus:
    """Ensure workspace-local runner venv has kernel/runtime dependencies installed."""
    return ensure_workspace_runner_environment(config, workspace_duckdb_path)


def ensure_workspace_runner_environment(
    config: ExecutionRuntimeConfig,
    workspace_duckdb_path: str,
) -> RunnerEnvironmentStatus:
    """Create/update the workspace runner venv and return its status."""
    venv_path = resolve_workspace_runner_venv(workspace_duckdb_path)
    venv_path.parent.mkdir(parents=True, exist_ok=True)
    runner_python = _python_bin_from_venv(venv_path)
    created = False
    if not runner_python.exists():
        _create_runner_venv(config, venv_path)
        created = True

    required_packages = _build_required_packages(config)
    marker_file = venv_path / ".inquira_runner_state"
    desired_state = _build_runner_state(required_packages, config.runner_index_url)
    existing_state = marker_file.read_text(encoding="utf-8").strip() if marker_file.exists() else ""

    packages_installed = False
    if created or existing_state != desired_state:
        _install_with_uv_or_pip(
            str(runner_python),
            required_packages,
            index_url=config.runner_index_url,
        )
        marker_file.write_text(desired_state, encoding="utf-8")
        packages_installed = True

    return RunnerEnvironmentStatus(
        venv_path=str(venv_path),
        python_executable=str(runner_python),
        created=created,
        packages_installed=packages_installed,
        packages=required_packages,
    )


def _build_required_packages(config: ExecutionRuntimeConfig) -> list[str]:
    # Plotly's mime renderer depends on nbformat; pin a modern range for Python 3.12 compatibility.
    defaults = [
        "ipykernel",
        "nbformat>=5.10.4",
        "narwhals",
        "duckdb",
        "pandas",
        "polars",
        "pyarrow",
        "plotly",
        "statsmodels",
        "scikit-learn",
    ]
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
    workspace_duckdb_path: str | None = None,
) -> RunnerInstallResult:
    if workspace_duckdb_path:
        ensure_workspace_runner_environment(config, workspace_duckdb_path)
    runner_python = resolve_runner_python(config, workspace_duckdb_path)
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


def _create_runner_venv(config: ExecutionRuntimeConfig, venv_path: Path) -> None:
    base_python = (config.runner_python_executable or "").strip() or sys.executable
    uv_cmd = ["uv", "venv", str(venv_path), "--python", base_python]
    uv_proc = subprocess.run(uv_cmd, capture_output=True, text=True)
    if uv_proc.returncode == 0:
        return

    py_cmd = [base_python, "-m", "venv", str(venv_path)]
    py_proc = subprocess.run(py_cmd, capture_output=True, text=True)
    if py_proc.returncode == 0:
        return

    uv_err = (uv_proc.stderr or uv_proc.stdout or "").strip()
    py_err = (py_proc.stderr or py_proc.stdout or "").strip()
    raise RuntimeError(
        "Failed to create workspace runner virtual environment. "
        f"uv error: {uv_err or '<none>'}; python -m venv error: {py_err or '<none>'}"
    )


def _python_bin_from_venv(venv_path: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _build_runner_state(packages: list[str], index_url: str | None) -> str:
    payload = {
        "packages": list(packages),
        "index_url": (index_url or "").strip(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
