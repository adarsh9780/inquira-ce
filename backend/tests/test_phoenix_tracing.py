from app.services import tracing


def test_backend_tracing_wrapper_uses_backend_section(monkeypatch):
    called = {}

    def fake_shared_init(**kwargs):
        called.update(kwargs)
        return True

    monkeypatch.setattr(tracing, "_load_shared_init", lambda: fake_shared_init)
    assert tracing.init_phoenix_tracing() is True
    assert called["section_path"] == ("backend", "phoenix")
    assert called["enabled_env"] == "INQUIRA_PHOENIX_ENABLED"
    assert called["project_env"] == "INQUIRA_PHOENIX_PROJECT"
    assert called["endpoint_env"] == "INQUIRA_PHOENIX_ENDPOINT"
    assert called["default_project"] == "inquira-dev"


def test_backend_tracing_reset_delegates_to_shared(monkeypatch):
    called = {"count": 0}

    def fake_shared_reset():
        called["count"] += 1

    monkeypatch.setattr(tracing, "_load_shared_reset", lambda: fake_shared_reset)
    tracing.reset_phoenix_tracing_state()
    assert called["count"] == 1
