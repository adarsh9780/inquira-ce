"""Helpers for summarizing execution results for result-focused explanations."""

from __future__ import annotations

import json
from typing import Any


def _truncate_text(value: Any, *, limit: int = 2000) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _json_preview(value: Any, *, limit: int = 3000) -> str:
    try:
        rendered = json.dumps(value, ensure_ascii=True, default=str)
    except Exception:
        rendered = str(value)
    return _truncate_text(rendered, limit=limit)


async def validate_and_summarize_result(
    *,
    workspace_id: str,
    run_id: str,
    execution_result: dict[str, Any],
    max_artifacts: int = 3,
    max_rows: int = 5,
) -> dict[str, Any]:
    _ = workspace_id, run_id, max_artifacts, max_rows
    artifacts = [
        item for item in (execution_result.get("artifacts") or []) if isinstance(item, dict)
    ]

    return {
        "success": bool(execution_result.get("success")),
        "stdout": _truncate_text(execution_result.get("stdout"), limit=1800),
        "stderr": _truncate_text(
            execution_result.get("stderr") or execution_result.get("error"),
            limit=1800,
        ),
        "result_type": str(execution_result.get("result_type") or ""),
        "result_kind": str(execution_result.get("result_kind") or ""),
        "result_name": str(execution_result.get("result_name") or ""),
        "result_preview": _json_preview(execution_result.get("result"), limit=1800),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
