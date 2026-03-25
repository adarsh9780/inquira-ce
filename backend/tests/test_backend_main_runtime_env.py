import app.main as backend_main


def test_backend_main_uses_env_runtime_host_and_port(monkeypatch):
    monkeypatch.setenv("INQUIRA_HOST", "127.0.0.1")
    monkeypatch.setenv("INQUIRA_PORT", "9102")

    assert backend_main._resolve_runtime_host() == "127.0.0.1"
    assert backend_main._resolve_runtime_port() == 9102


def test_backend_main_runtime_port_falls_back_for_invalid_values(monkeypatch):
    monkeypatch.setenv("INQUIRA_PORT", "not-a-number")
    assert backend_main._resolve_runtime_port() == 8000

    monkeypatch.setenv("INQUIRA_PORT", "0")
    assert backend_main._resolve_runtime_port() == 8000
