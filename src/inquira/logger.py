from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


LOG_DIR = Path.home() / ".inquira" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_configured = False


def _get_env_level(default: str = "INFO") -> str:
    return os.getenv("LOG_LEVEL", default).upper()


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
        # Fallback: no Loguru available. Use simple stdio printer.
        # We still expose logprint() but without advanced features.
        _configured = True
        return

    _logger.remove()

    level = _get_env_level()

    # Console sink (pretty), non-blocking
    _logger.add(
        sys.stdout,
        colorize=True,
        backtrace=False,
        diagnose=False,
        enqueue=True,  # non-blocking
        level=level,
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
        level=level,
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
        _logger.opt(depth=max(1, int(caller_depth))).bind(**bind_kwargs).log(level.upper(), message)
    except Exception:
        # Fallback: best-effort stdout if Loguru not available
        # Include extra fields as a simple suffix
        if extra:
            suffix = " " + " ".join(f"{k}={v}" for k, v in extra.items())
        else:
            suffix = ""
        sys.stdout.write(message + suffix + "\n")
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
