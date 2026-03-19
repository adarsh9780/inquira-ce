from __future__ import annotations

import sys
from pathlib import Path

# Ensure shared modules at repo root are importable in agent test runs.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.observability import phoenix


def test_shared_phoenix_uses_agent_service_section(monkeypatch, tmp_path):
    called = {}

    def fake_register(**kwargs):
        called.update(kwargs)
        return object()

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[agent_service.phoenix]
enabled = true
project = "agent-from-toml"
endpoint = "http://127.0.0.1:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_ENABLED", raising=False)
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_PROJECT", raising=False)
    monkeypatch.delenv("INQUIRA_AGENT_PHOENIX_ENDPOINT", raising=False)
    phoenix.reset_phoenix_tracing_state()

    assert (
        phoenix.init_phoenix_tracing(
            section_path=("agent_service", "phoenix"),
            enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
            project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
            endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
            default_project="inquira-agent",
            load_register=lambda: fake_register,
        )
        is True
    )
    assert called["auto_instrument"] is True
    assert called["project_name"] == "agent-from-toml"
    assert called["endpoint"] == "http://127.0.0.1:6006/v1/traces"


def test_shared_phoenix_env_overrides_toml(monkeypatch, tmp_path):
    called = {}

    def fake_register(**kwargs):
        called.update(kwargs)
        return object()

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[agent_service.phoenix]
enabled = false
project = "from-toml"
endpoint = "http://toml:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_ENABLED", "true")
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_PROJECT", "from-env")
    monkeypatch.setenv("INQUIRA_AGENT_PHOENIX_ENDPOINT", "http://env:6006/v1/traces")
    phoenix.reset_phoenix_tracing_state()

    assert (
        phoenix.init_phoenix_tracing(
            section_path=("agent_service", "phoenix"),
            enabled_env="INQUIRA_AGENT_PHOENIX_ENABLED",
            project_env="INQUIRA_AGENT_PHOENIX_PROJECT",
            endpoint_env="INQUIRA_AGENT_PHOENIX_ENDPOINT",
            default_project="inquira-agent",
            load_register=lambda: fake_register,
        )
        is True
    )
    assert called["project_name"] == "from-env"
    assert called["endpoint"] == "http://env:6006/v1/traces"

