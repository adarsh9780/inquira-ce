from __future__ import annotations

from agent_v2.runtime import load_agent_runtime_config


def test_agent_runtime_config_reads_backend_base_url_and_shared_secret(tmp_path, monkeypatch):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[backend]
host = "127.0.0.1"
port = 9001
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.setenv("INQUIRA_AGENT_SHARED_SECRET", "secret-123")
    load_agent_runtime_config.cache_clear()

    resolved = load_agent_runtime_config()

    assert resolved.backend_base_url == "http://127.0.0.1:9001"
    assert resolved.backend_shared_secret == "secret-123"
    load_agent_runtime_config.cache_clear()
