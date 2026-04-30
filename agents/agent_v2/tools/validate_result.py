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


def _normalize_artifacts(raw: Any, *, max_items: int) -> list[dict[str, Any]]:
    artifacts = raw if isinstance(raw, list) else []
    normalized: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "artifact_id": str(item.get("artifact_id") or "").strip(),
                "name": str(item.get("name") or "").strip(),
                "kind": str(item.get("kind") or "").strip().lower(),
                "path": str(item.get("path") or "").strip(),
                "mime_type": str(item.get("mime_type") or "").strip(),
            }
        )
        if len(normalized) >= max_items:
            break
    return normalized


def _infer_result_kind(
    *,
    execution_result: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> str:
    explicit = str(execution_result.get("result_kind") or "").strip().lower()
    if explicit:
        return explicit

    result_type = str(execution_result.get("result_type") or "").strip().lower()
    if "dataframe" in result_type:
        return "dataframe"
    if "figure" in result_type or "plotly" in result_type or "matplotlib" in result_type:
        return "figure"

    artifact_kinds = {str(item.get("kind") or "").strip().lower() for item in artifacts}
    if "dataframe" in artifact_kinds:
        return "dataframe"
    if "figure" in artifact_kinds:
        return "figure"

    result_value = execution_result.get("result")
    if isinstance(result_value, (int, float, bool, str)):
        return "scalar"
    if isinstance(result_value, list):
        return "dataframe"
    if isinstance(result_value, dict):
        return "object"
    return "none"


def _result_preview(value: Any, *, max_rows: int = 5, limit: int = 1800) -> str:
    if isinstance(value, list):
        return _json_preview(value[: max(1, int(max_rows))], limit=limit)
    if isinstance(value, dict):
        preview = dict(value)
        rows = preview.get("rows")
        if isinstance(rows, list):
            preview["rows"] = rows[: max(1, int(max_rows))]
        return _json_preview(preview, limit=limit)
    return _json_preview(value, limit=limit)


def _row_count_preview(value: Any) -> int | None:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        rows = value.get("rows")
        if isinstance(rows, list):
            return len(rows)
    return None


async def validate_and_summarize_result(
    *,
    workspace_id: str,
    run_id: str,
    execution_result: dict[str, Any],
    max_artifacts: int = 3,
    max_rows: int = 5,
) -> dict[str, Any]:
    _ = workspace_id, run_id
    safe_max_artifacts = max(1, min(10, int(max_artifacts)))
    safe_max_rows = max(1, min(20, int(max_rows)))
    artifacts = _normalize_artifacts(
        execution_result.get("artifacts"),
        max_items=safe_max_artifacts,
    )
    result_kind = _infer_result_kind(execution_result=execution_result, artifacts=artifacts)
    stdout = _truncate_text(execution_result.get("stdout"), limit=1800)
    stderr = _truncate_text(
        execution_result.get("stderr") or execution_result.get("error"),
        limit=1800,
    )
    result_preview = _result_preview(
        execution_result.get("result"),
        max_rows=safe_max_rows,
        limit=1800,
    )
    row_count_preview = _row_count_preview(execution_result.get("result"))
    has_tabular_signal = result_kind == "dataframe" or row_count_preview is not None
    is_empty_result = bool(has_tabular_signal and row_count_preview == 0)
    has_signal = bool(stdout or artifacts or (result_kind not in {"", "none"}))

    return {
        "success": bool(execution_result.get("success")),
        "stdout": stdout,
        "stderr": stderr,
        "result_type": str(execution_result.get("result_type") or ""),
        "result_kind": result_kind,
        "result_name": str(execution_result.get("result_name") or ""),
        "result_preview": result_preview,
        "row_count_preview": row_count_preview,
        "has_tabular_signal": has_tabular_signal,
        "is_empty_result": is_empty_result,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "artifact_kinds": [str(item.get("kind") or "").strip().lower() for item in artifacts],
        "has_signal": has_signal,
    }
