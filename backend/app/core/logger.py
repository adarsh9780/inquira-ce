from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_DIR = Path.home() / ".inquira" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_configured = False
_fallback_console_level = "ERROR"
_fallback_file_level = "DEBUG"
_fallback_color_errors = True

_LEVEL_VALUES = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "SUCCESS": 25,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


def _normalize_level(level: str, default: str) -> str:
    candidate = str(level or "").upper()
    return candidate if candidate in _LEVEL_VALUES else default


def _load_logging_config() -> tuple[str, str, bool]:
    # Defaults match requested behavior.
    console_level = "ERROR"
    file_level = "DEBUG"
    color_errors = True

    try:
        default_cfg = Path(__file__).parent.parent / "app_config.json"
        user_cfg = Path.home() / ".inquira" / "config.json"

        merged = {}
        if default_cfg.exists():
            merged.update(json.loads(default_cfg.read_text(encoding="utf-8")))
        if user_cfg.exists():
            merged.update(json.loads(user_cfg.read_text(encoding="utf-8")))

        logging_cfg = merged.get("LOGGING") or {}
        if isinstance(logging_cfg, dict):
            console_level = _normalize_level(logging_cfg.get("console_level"), console_level)
            file_level = _normalize_level(logging_cfg.get("file_level"), file_level)
            color_errors = bool(logging_cfg.get("color_errors", color_errors))
    except Exception:
        pass

    return console_level, file_level, color_errors


def _should_emit(level: str, threshold: str) -> bool:
    return _LEVEL_VALUES.get(level, 0) >= _LEVEL_VALUES.get(threshold, 0)


def _format_fallback_console(message: str, level: str) -> str:
    if not _fallback_color_errors:
        return message
    if level not in {"ERROR", "CRITICAL"}:
        return message
    try:
        from colorama import Fore, Style, init

        init(autoreset=True)
        return f"{Fore.RED}{message}{Style.RESET_ALL}"
    except Exception:
        return message


def _write_fallback_file(message: str, level: str, extra: dict[str, Any]) -> None:
    try:
        payload = {
            "time": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "extra": extra or {},
        }
        log_file = LOG_DIR / f"app_{datetime.now():%Y%m%d}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass


def init_logger() -> None:
    """Configure logging sinks.

    - Pretty console output (colorized)
    - JSON file logs with rotation/retention
    - Non-blocking via queue (enqueue)

    Idempotent: safe to call multiple times.
    """
    global _configured
    if _configured:
        return

    try:
        from loguru import logger as _logger
    except Exception:
        # Fallback mode: still honor level filtering and file logging.
        global _fallback_console_level, _fallback_file_level, _fallback_color_errors
        _fallback_console_level, _fallback_file_level, _fallback_color_errors = _load_logging_config()
        if _fallback_color_errors:
            try:
                from colorama import init

                init(autoreset=True)
            except Exception:
                pass
        _configured = True
        return

    _logger.remove()

    console_level, file_level, _ = _load_logging_config()

    # Console sink (pretty), non-blocking
    _logger.add(
        sys.stdout,
        colorize=True,
        backtrace=False,
        diagnose=False,
        enqueue=True,  # non-blocking
        level=console_level,
        filter=lambda record: record["extra"].get("to_console", True),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "{extra[request_id]:^12} | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
    )

    # JSONL rotating file, non-blocking
    _logger.add(
        LOG_DIR / "app_{time:YYYYMMDD}.jsonl",
        rotation="10 MB",          # size-based rotation
        retention="14 days",       # keep last 14 days
        compression="zip",         # compress old logs
        level=file_level,
        enqueue=True,
        filter=lambda record: record["extra"].get("to_file", True),
        serialize=True,            # JSON output
    )

    _configured = True


def logprint(
    *args: Any,
    level: str = "INFO",
    to_console: bool | None = None,
    to_file: bool | None = None,
    caller_depth: int = 1,
    **extra: Any,
) -> None:
    """Drop-in replacement for print() with structured logging.

    - Accepts any number of positional args; joined with spaces like print.
    - Keyword args become structured fields (parseable in JSON logs).
    - Level can be one of: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL.
    - Non-blocking and rotating file behavior configured via init_logger().
    """
    init_logger()

    message = " ".join(str(a) for a in args)
    level_upper = _normalize_level(level, "INFO")

    try:
        from loguru import logger as _logger
        bind_kwargs = dict(**extra)
        # Ensure required extras exist for formatting and filters
        if "request_id" not in bind_kwargs:
            bind_kwargs["request_id"] = "-"
        if to_console is not None:
            bind_kwargs["to_console"] = bool(to_console)
        if to_file is not None:
            bind_kwargs["to_file"] = bool(to_file)
        # Remove internal-only field if passed via wrappers
        bind_kwargs.pop("caller_depth", None)
        # Always bind so format placeholders are satisfied and attribute to caller frame
        _logger.opt(depth=max(1, int(caller_depth))).bind(**bind_kwargs).log(level_upper, message)
    except Exception:
        # Fallback mode with explicit level filtering.
        suffix = ""
        if extra:
            suffix = " " + " ".join(f"{k}={v}" for k, v in extra.items())
        line = message + suffix

        if _should_emit(level_upper, _fallback_file_level):
            _write_fallback_file(message=line, level=level_upper, extra=extra)

        if _should_emit(level_upper, _fallback_console_level):
            sys.stdout.write(_format_fallback_console(line, level_upper) + "\n")
            sys.stdout.flush()


def patch_print() -> None:
    """Monkey-patch builtins.print to route through logprint.

    Useful to capture legacy print() calls without editing all call sites.
    """
    import builtins

    original_print = builtins.print  # keep reference to avoid recursion

    def _wrapped_print(*args: Any, **kwargs: Any) -> None:
        # Preserve original kwargs for potential fallback
        original_kwargs = dict(kwargs)

        # If printing to anything other than stdout (e.g., stderr), bypass log routing
        file_obj = original_kwargs.get("file", None)
        if file_obj is not None and file_obj is not sys.stdout:
            return original_print(*args, **original_kwargs)

        try:
            # Extract logging-specific kwargs (do not forward to structured extras)
            lvl = kwargs.pop("level", "INFO")
            to_console = kwargs.pop("to_console", None)
            to_file = kwargs.pop("to_file", None)

            # Drop standard print kwargs so they don't end up in JSON extras
            kwargs.pop("file", None)
            kwargs.pop("sep", None)
            kwargs.pop("end", None)
            kwargs.pop("flush", None)

            # Route to structured logger; depth=2 to attribute to the real caller
            logprint(
                *args,
                level=lvl,
                to_console=to_console,
                to_file=to_file,
                caller_depth=2,
                **kwargs,
            )
        except Exception:
            # On any failure, fall back to the original print to avoid loops
            return original_print(*args, **original_kwargs)

    builtins.print = _wrapped_print  # type: ignore


__all__ = ["init_logger", "logprint", "patch_print", "LOG_DIR"]
