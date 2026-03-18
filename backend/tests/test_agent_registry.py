from pathlib import Path

from app.agent_v2.registry import get_agent_bindings
from app.agent_v2.runtime import load_agent_runtime_config


def _write_toml(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _clear_registry_cache() -> None:
    load_agent_runtime_config.cache_clear()
    get_agent_bindings.cache_clear()


def test_agent_registry_returns_v2_bindings(tmp_path, monkeypatch):
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

    assert runtime.max_tool_calls == 5
    assert bindings.version == "agent_v2"
    assert callable(bindings.build_graph)
    assert callable(bindings.build_input_state)

    _clear_registry_cache()


def test_agent_runtime_config_reads_v2_limits_from_toml(tmp_path, monkeypatch):
    cfg = tmp_path / "inquira.toml"
    _write_toml(
        cfg,
        """
[agent]
version = "unknown"
max-tool-calls = 11
max-code-executions = 7

[agent.intervention]
timeout-seconds = 45
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    _clear_registry_cache()

    runtime = load_agent_runtime_config()
    assert runtime.max_tool_calls == 11
    assert runtime.max_code_executions == 7
    assert runtime.intervention_timeout_seconds == 45

    _clear_registry_cache()
