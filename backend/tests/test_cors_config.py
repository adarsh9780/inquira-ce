import importlib
import sys
from pathlib import Path


def _load_main_module():
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    return importlib.import_module("app.main")


def test_load_cors_origins_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    main = _load_main_module()
    origins = main._load_cors_origins()
    assert "http://localhost:5173" in origins
    assert "https://tauri.localhost" in origins


def test_load_cors_origins_from_comma_separated_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,https://app.example.com")
    main = _load_main_module()
    origins = main._load_cors_origins()
    assert origins == ["http://localhost:5173", "https://app.example.com"]
