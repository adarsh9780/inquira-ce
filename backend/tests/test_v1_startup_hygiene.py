from pathlib import Path


def _main_source() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "backend" / "app" / "main.py").read_text(encoding="utf-8")


def test_main_no_longer_initializes_legacy_database_manager():
    source = _main_source()
    assert "from .database.database_manager import DatabaseManager" not in source
    assert "app.state.db_manager = DatabaseManager(app.state.config)" not in source


def test_main_websocket_flow_avoids_legacy_settings_database_imports():
    source = _main_source()
    assert "from .database.database import get_user_settings" not in source
