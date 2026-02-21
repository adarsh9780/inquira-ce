import importlib
import json
import sys
from types import SimpleNamespace


class _DummyLoguruLogger:
    def __init__(self):
        self.add_calls = []
        self.remove_called = False

    def remove(self):
        self.remove_called = True

    def add(self, *args, **kwargs):
        self.add_calls.append({"args": args, "kwargs": kwargs})


def test_init_logger_uses_error_for_console_and_debug_for_file(monkeypatch):
    from app.core import logger as logger_module

    dummy_logger = _DummyLoguruLogger()
    monkeypatch.setitem(
        sys.modules, "loguru", SimpleNamespace(logger=dummy_logger)
    )

    logger_module = importlib.reload(logger_module)
    logger_module._configured = False
    logger_module.init_logger()

    assert dummy_logger.remove_called is True
    assert len(dummy_logger.add_calls) == 2
    console_call, file_call = dummy_logger.add_calls
    assert console_call["kwargs"]["level"] == "ERROR"
    assert file_call["kwargs"]["level"] == "DEBUG"


def test_load_logging_config_reads_user_overrides(monkeypatch, tmp_path):
    from app.core import logger as logger_module

    logger_module = importlib.reload(logger_module)

    # Prepare ~/.inquira/config.json with logging overrides
    fake_home = tmp_path / "home"
    cfg_dir = fake_home / ".inquira"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.json").write_text(
        json.dumps(
            {
                "LOGGING": {
                    "console_level": "CRITICAL",
                    "file_level": "INFO",
                    "color_errors": False,
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(logger_module.Path, "home", staticmethod(lambda: fake_home))

    console_level, file_level, color_errors = logger_module._load_logging_config()
    assert console_level == "CRITICAL"
    assert file_level == "INFO"
    assert color_errors is False


def test_should_emit_respects_levels():
    from app.core import logger as logger_module

    assert logger_module._should_emit("ERROR", "ERROR") is True
    assert logger_module._should_emit("CRITICAL", "ERROR") is True
    assert logger_module._should_emit("DEBUG", "ERROR") is False
