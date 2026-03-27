from app.core import logger as logger_module


class _Cp1252Stdout:
    encoding = "cp1252"

    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, text: str) -> int:
        # Mirror Windows cp1252 console behavior: fail on non-encodable chars.
        text.encode("cp1252")
        self.writes.append(text)
        return len(text)

    def flush(self) -> None:
        return


def test_encode_console_safe_escapes_non_cp1252_characters():
    rendered = logger_module._encode_console_safe("❌ stream failure", "cp1252")

    assert "\\u274c" in rendered
    assert "stream failure" in rendered


def test_write_fallback_console_handles_cp1252_encoding_errors(monkeypatch):
    fake_stdout = _Cp1252Stdout()
    monkeypatch.setattr(logger_module.sys, "stdout", fake_stdout)

    logger_module._write_fallback_console("❌ stream failure", "ERROR")

    assert fake_stdout.writes
