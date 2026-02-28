"""Helpers for mapping Jupyter IOPub messages to Inquira execution payloads."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

_ANSI_PATTERN = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


@dataclass
class ParsedExecutionOutput:
    """Aggregated output collected from a single Jupyter execution request."""

    stdout_parts: list[str] = field(default_factory=list)
    stderr_parts: list[str] = field(default_factory=list)
    error: str | None = None
    result: Any | None = None
    result_type: str | None = None

    def as_response(self) -> dict[str, Any]:
        """Return the legacy execution payload consumed by the frontend."""
        stdout = "".join(self.stdout_parts).strip()
        stderr = "".join(self.stderr_parts).strip()
        has_stdout = bool(stdout)
        has_stderr = bool(stderr)
        success = self.error is None and not stderr
        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "has_stdout": has_stdout,
            "has_stderr": has_stderr,
            "error": self.error if not success else None,
            "result": self.result,
            "result_type": self.result_type,
        }


def update_from_iopub_message(
    output: ParsedExecutionOutput,
    msg_type: str,
    content: dict[str, Any],
) -> None:
    """Update aggregated output using a single IOPub message."""
    if msg_type == "stream":
        _handle_stream(output, content)
        return
    if msg_type == "error":
        _handle_error(output, content)
        return
    if msg_type in {"display_data", "execute_result"}:
        _handle_rich_output(output, content)


def _handle_stream(output: ParsedExecutionOutput, content: dict[str, Any]) -> None:
    name = str(content.get("name", "stdout"))
    text = _strip_ansi(str(content.get("text", "")))
    if name == "stderr":
        output.stderr_parts.append(text)
    else:
        output.stdout_parts.append(text)


def _handle_error(output: ParsedExecutionOutput, content: dict[str, Any]) -> None:
    traceback_lines = content.get("traceback")
    if isinstance(traceback_lines, list) and traceback_lines:
        traceback_text = "\n".join(_strip_ansi(str(line)) for line in traceback_lines)
    else:
        ename = str(content.get("ename", "ExecutionError"))
        evalue = str(content.get("evalue", ""))
        traceback_text = _strip_ansi(f"{ename}: {evalue}".strip())
    output.stderr_parts.append(traceback_text + "\n")
    output.error = traceback_text


def _handle_rich_output(output: ParsedExecutionOutput, content: dict[str, Any]) -> None:
    data = content.get("data")
    if not isinstance(data, dict):
        return
    value, value_type = _extract_best_effort_result(data)
    if value_type is None:
        return
    output.result = value
    output.result_type = value_type


def _extract_best_effort_result(data: dict[str, Any]) -> tuple[Any | None, str | None]:
    if "application/vnd.plotly.v1+json" in data:
        fig = data.get("application/vnd.plotly.v1+json")
        return fig, "Figure"

    if "application/json" in data:
        value = data.get("application/json")
        return value, _classify_result_type(value)

    if "text/plain" in data:
        text = _strip_ansi(str(data.get("text/plain", "")))
        parsed = _parse_text_plain_scalar(text)
        return parsed, "scalar"

    if "text/html" in data:
        html = str(data.get("text/html", ""))
        return html, "scalar"

    return None, None


def _classify_result_type(value: Any) -> str:
    if isinstance(value, dict) and {"columns", "data"}.issubset(value.keys()):
        return "DataFrame"
    if isinstance(value, dict) and {"data", "layout"}.issubset(value.keys()):
        return "Figure"
    return "scalar"


def _parse_text_plain_scalar(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return ""
    try:
        return ast.literal_eval(stripped)
    except Exception:
        return stripped


def _strip_ansi(text: str) -> str:
    """Remove ANSI color/control escape codes from terminal-formatted text."""
    return _ANSI_PATTERN.sub("", text)
