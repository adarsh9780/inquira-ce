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
url = "https://deployment.example.com"
host = "127.0.0.1"
port = 9133
expected_api_major = 3
startup_timeout_sec = 99
default_agent = "agent_v1"
manage_assistants = false
recursion_limit = 120

[agent_service.auth]
mode = "bearer"
api_key = "langsmith-token"
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_agent_service_config.cache_clear()

    resolved = load_agent_service_config()

    assert resolved.url == "https://deployment.example.com"
    assert resolved.host == "127.0.0.1"
    assert resolved.port == 9133
    assert resolved.expected_api_major == 3
    assert resolved.startup_timeout_sec == 99
    assert resolved.default_agent == "agent_v1"
    assert resolved.auth_mode == "bearer"
    assert resolved.api_key == "langsmith-token"
    assert resolved.manage_assistants is False
    assert resolved.recursion_limit == 120
    assert resolved.base_url == "https://deployment.example.com"

    load_agent_service_config.cache_clear()


def test_agent_service_config_env_overrides_url_and_auth(tmp_path, monkeypatch):
    cfg_path = tmp_path / "inquira.toml"
    _write(
        cfg_path,
        """
[agent_service]
host = "127.0.0.1"
port = 8123

[agent_service.auth]
mode = "shared_secret"
shared_secret = "file-secret"
""".strip(),
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    monkeypatch.setenv("INQUIRA_AGENT_URL", "https://agents.example.com/")
    monkeypatch.setenv("INQUIRA_AGENT_AUTH_MODE", "x_api_key")
    monkeypatch.setenv("INQUIRA_AGENT_API_KEY", "env-token")
    monkeypatch.setenv("INQUIRA_AGENT_MANAGE_ASSISTANTS", "false")
    monkeypatch.setenv("INQUIRA_AGENT_RECURSION_LIMIT", "95")
    load_agent_service_config.cache_clear()

    resolved = load_agent_service_config()

    assert resolved.base_url == "https://agents.example.com"
    assert resolved.auth_mode == "x_api_key"
    assert resolved.api_key == "env-token"
    assert resolved.manage_assistants is False
    assert resolved.recursion_limit == 95

    load_agent_service_config.cache_clear()
