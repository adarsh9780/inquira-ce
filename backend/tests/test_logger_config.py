import importlib
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
