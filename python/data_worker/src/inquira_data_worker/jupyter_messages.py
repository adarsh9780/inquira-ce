"""Parse Jupyter IOPub messages into a stable execution response."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Callable

_ANSI = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


@dataclass
class ExecutionOutput:
    stdout_parts: list[str] = field(default_factory=list)
    stderr_parts: list[str] = field(default_factory=list)
    error: str | None = None
    result: Any = None
    result_kind: str | None = None

    def update(self, message_type: str, content: dict[str, Any], emit: Callable[[dict[str, Any]], Any] | None = None) -> None:
        if message_type == "stream":
            name = str(content.get("name") or "stdout")
            text = _strip_ansi(str(content.get("text") or ""))
            (self.stderr_parts if name == "stderr" else self.stdout_parts).append(text)
            if emit is not None:
                emit({"type": "stream", "name": name, "text": text})
            return
        if message_type == "error":
            traceback = content.get("traceback")
            if isinstance(traceback, list) and traceback:
                text = "\n".join(_strip_ansi(str(line)) for line in traceback)
            else:
                text = _strip_ansi(f"{content.get('ename', 'ExecutionError')}: {content.get('evalue', '')}".strip())
            self.stderr_parts.append(text + "\n")
            self.error = text
            return
        if message_type not in {"display_data", "execute_result"}:
            return
        data = content.get("data")
        if not isinstance(data, dict):
            return
        if "application/json" in data:
            value = data["application/json"]
            if isinstance(value, dict) and value.get("kind") in {"dataframe", "figure", "scalar", "text", "exports"}:
                self.result_kind = str(value["kind"])
                self.result = value.get("value")
            else:
                self.result = value
                self.result_kind = "scalar"
            return
        if "application/vnd.plotly.v1+json" in data:
            self.result = data["application/vnd.plotly.v1+json"]
            self.result_kind = "figure"
            return
        if "text/plain" in data:
            text = _strip_ansi(str(data["text/plain"])).strip()
            try:
                self.result = ast.literal_eval(text)
            except Exception:
                self.result = text
            self.result_kind = "scalar"

    def response(self) -> dict[str, Any]:
        stdout = "".join(self.stdout_parts)
        stderr = "".join(self.stderr_parts)
        return {
            "success": self.error is None,
            "stdout": stdout,
            "stderr": stderr,
            "has_stdout": bool(stdout),
            "has_stderr": bool(stderr),
            "error": self.error,
            "result": self.result,
            "result_kind": self.result_kind,
        }


def _strip_ansi(value: str) -> str:
    return _ANSI.sub("", value)
