from types import SimpleNamespace

import pytest

from app.services import runner_env


def _cfg(**overrides):
    base = {
        "runner_python_executable": "/tmp/runner-python",
        "runner_packages": ["pyarrow"],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_required_packages_includes_defaults_and_dedupes():
    packages = runner_env._build_required_packages(
        _cfg(runner_packages=["duckdb", "PyArrow", "ipykernel"])
    )
    assert "duckdb" in packages
    assert "ipykernel" in packages
    assert "nbformat>=5.10.4" in packages
    assert "pandas" in packages
    assert "plotly" in packages
    assert "polars" in packages
    assert "statsmodels" in packages
    assert "scikit-learn" in packages
    assert any(pkg.lower() == "pyarrow" for pkg in packages)


def test_resolve_runner_python_requires_path():
    with pytest.raises(RuntimeError):
        runner_env.resolve_runner_python(_cfg(runner_python_executable=""))


def test_resolve_workspace_runner_venv_uses_workspace_root(tmp_path):
    duckdb_path = tmp_path / "workspace-1" / "workspace.duckdb"
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    duckdb_path.touch()

    venv_path = runner_env.resolve_workspace_runner_venv(str(duckdb_path))
    assert venv_path == duckdb_path.parent / ".venv"


def test_ensure_workspace_pyproject_bootstraps_missing_metadata(tmp_path):
    duckdb_path = tmp_path / "workspace-2" / "workspace.duckdb"
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    duckdb_path.touch()

    runner_env._ensure_workspace_pyproject(str(duckdb_path))
    pyproject = duckdb_path.parent / "pyproject.toml"

    assert pyproject.exists() is True
    content = pyproject.read_text(encoding="utf-8")
    assert "[project]" in content
    assert 'name = "workspace-2"' in content
