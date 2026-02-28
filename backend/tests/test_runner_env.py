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
    assert "nbformat>=4.2.0" in packages
    assert "pandas" in packages
    assert "plotly" in packages
    assert "PyArrow" in packages


def test_resolve_runner_python_requires_path():
    with pytest.raises(RuntimeError):
        runner_env.resolve_runner_python(_cfg(runner_python_executable=""))
