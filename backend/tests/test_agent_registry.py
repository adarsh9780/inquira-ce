from pathlib import Path

from app.agent.registry import get_agent_bindings, load_agent_runtime_config


def _write_toml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _clear_registry_cache() -> None:
    load_agent_runtime_config.cache_clear()
    get_agent_bindings.cache_clear()


def test_agent_registry_uses_v2_when_enabled(tmp_path, monkeypatch):
    cfg = tmp_path / "inquira.toml"
    _write_toml(
        cfg,
        """
[agent]
version = "agent_v2"
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    _clear_registry_cache()

    runtime = load_agent_runtime_config()
    bindings = get_agent_bindings()

    assert runtime.version == "agent_v2"
    assert bindings.version == "agent_v2"
    assert callable(bindings.build_graph)
    assert callable(bindings.build_input_state)

    _clear_registry_cache()


def test_agent_registry_falls_back_to_v1_for_unknown_version(tmp_path, monkeypatch):
    cfg = tmp_path / "inquira.toml"
    _write_toml(
        cfg,
        """
[agent]
version = "unknown"
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    _clear_registry_cache()

    runtime = load_agent_runtime_config()
    bindings = get_agent_bindings()

    assert runtime.version == "agent_v1"
    assert bindings.version == "agent_v1"

    _clear_registry_cache()
