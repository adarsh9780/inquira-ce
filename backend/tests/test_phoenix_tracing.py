from app.services import tracing


def test_phoenix_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("INQUIRA_PHOENIX_ENABLED", raising=False)
    tracing._tracing_initialized = False
    assert tracing.init_phoenix_tracing() is False


def test_phoenix_tracing_register_called_with_auto_instrument(monkeypatch):
    called = {}

    def fake_register(**kwargs):
        called.update(kwargs)
        return object()

    monkeypatch.setenv("INQUIRA_PHOENIX_ENABLED", "true")
    monkeypatch.setenv("INQUIRA_PHOENIX_PROJECT", "inquira-test")
    monkeypatch.setenv("INQUIRA_PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
    monkeypatch.setattr(tracing, "_load_register", lambda: fake_register)

    tracing._tracing_initialized = False
    assert tracing.init_phoenix_tracing() is True
    assert called["auto_instrument"] is True
    assert called["project_name"] == "inquira-test"
    assert called["endpoint"] == "http://localhost:6006/v1/traces"


def test_phoenix_tracing_uses_inquira_toml_when_env_missing(monkeypatch, tmp_path):
    called = {}

    def fake_register(**kwargs):
        called.update(kwargs)
        return object()

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[backend.phoenix]
enabled = true
project = "inquira-toml"
endpoint = "http://127.0.0.1:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.delenv("INQUIRA_PHOENIX_ENABLED", raising=False)
    monkeypatch.delenv("INQUIRA_PHOENIX_PROJECT", raising=False)
    monkeypatch.delenv("INQUIRA_PHOENIX_ENDPOINT", raising=False)
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.setattr(tracing, "_load_register", lambda: fake_register)

    tracing._tracing_initialized = False
    assert tracing.init_phoenix_tracing() is True
    assert called["auto_instrument"] is True
    assert called["project_name"] == "inquira-toml"
    assert called["endpoint"] == "http://127.0.0.1:6006/v1/traces"


def test_phoenix_env_overrides_inquira_toml(monkeypatch, tmp_path):
    called = {}

    def fake_register(**kwargs):
        called.update(kwargs)
        return object()

    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        """
[backend.phoenix]
enabled = false
project = "from-toml"
endpoint = "http://toml:6006/v1/traces"
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.setenv("INQUIRA_PHOENIX_ENABLED", "true")
    monkeypatch.setenv("INQUIRA_PHOENIX_PROJECT", "from-env")
    monkeypatch.setenv("INQUIRA_PHOENIX_ENDPOINT", "http://env:6006/v1/traces")
    monkeypatch.setattr(tracing, "_load_register", lambda: fake_register)

    tracing._tracing_initialized = False
    assert tracing.init_phoenix_tracing() is True
    assert called["project_name"] == "from-env"
    assert called["endpoint"] == "http://env:6006/v1/traces"
