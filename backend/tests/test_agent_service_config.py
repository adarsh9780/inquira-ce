from pathlib import Path

from app.services.agent_service_config import load_agent_service_config


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_agent_service_config_loads_expected_fields(tmp_path, monkeypatch):
    cfg_path = tmp_path / "inquira.toml"
    _write(
        cfg_path,
        """
[agent_service]
host = "127.0.0.1"
port = 9133
expected_api_major = 3
startup_timeout_sec = 99
default_agent = "agent_v1"

[agent_service.auth]
mode = "shared_secret"
shared_secret = "local-secret"
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_agent_service_config.cache_clear()

    resolved = load_agent_service_config()

    assert resolved.host == "127.0.0.1"
    assert resolved.port == 9133
    assert resolved.expected_api_major == 3
    assert resolved.startup_timeout_sec == 99
    assert resolved.default_agent == "agent_v1"
    assert resolved.auth_mode == "shared_secret"
    assert resolved.shared_secret == "local-secret"
    assert resolved.base_url == "http://127.0.0.1:9133"

    load_agent_service_config.cache_clear()
