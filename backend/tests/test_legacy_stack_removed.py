from importlib import import_module
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "app.api.auth",
        "app.api.chat",
        "app.api.settings",
        "app.agent",
        "app.agent.graph",
        "app.agent.registry",
        "app.agent.events",
        "app.agent.code_guard",
        "app.database.database",
        "app.database.database_manager",
        "app.core.path_utils",
    ],
)
def test_removed_legacy_modules_fail_fast(module_name):
    with pytest.raises(ModuleNotFoundError):
        import_module(module_name)


def test_legacy_source_directories_removed():
    root = Path(__file__).resolve().parents[1] / "app"
    assert (root / "api").exists() is False
    assert (root / "agent").exists() is False
    assert (root / "database").exists() is False
    assert (root / "core" / "path_utils.py").exists() is False
