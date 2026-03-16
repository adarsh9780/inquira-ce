"""Helpers for summarizing execution results for result-focused explanations."""

from __future__ import annotations

import json
from typing import Any

from ...services.code_executor import (
    get_workspace_artifact_metadata_via_kernel,
    get_workspace_dataframe_rows,
    get_workspace_run_exports,
)


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
    """Build a compact, LLM-safe summary of the execution output."""
    artifacts = [
        item for item in (execution_result.get("artifacts") or []) if isinstance(item, dict)
    ]
    if not artifacts:
        try:
            exports = await get_workspace_run_exports(workspace_id=workspace_id, run_id=run_id)
        except Exception:
            exports = []
        artifacts = [item for item in exports if isinstance(item, dict)]

    summary: dict[str, Any] = {
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
        "artifacts": [],
    }

    for artifact in artifacts[: max(1, int(max_artifacts))]:
        if not isinstance(artifact, dict):
            continue
        item: dict[str, Any] = {
            "artifact_id": str(artifact.get("artifact_id") or ""),
            "logical_name": str(artifact.get("logical_name") or ""),
            "kind": str(artifact.get("kind") or ""),
            "row_count": artifact.get("row_count"),
            "columns": artifact.get("schema") if isinstance(artifact.get("schema"), list) else None,
        }
        kind = str(artifact.get("kind") or "").strip().lower()
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        row_count = int(artifact.get("row_count") or 0)

        if kind == "dataframe" and artifact_id:
            try:
                head = await get_workspace_dataframe_rows(
                    workspace_id=workspace_id,
                    artifact_id=artifact_id,
                    offset=0,
                    limit=max_rows,
                )
            except Exception:
                head = None
            if isinstance(head, dict):
                item["columns"] = head.get("columns") or item.get("columns")
                item["head_rows"] = head.get("rows") or []

            if row_count > max_rows:
                try:
                    tail = await get_workspace_dataframe_rows(
                        workspace_id=workspace_id,
                        artifact_id=artifact_id,
                        offset=max(0, row_count - max_rows),
                        limit=max_rows,
                    )
                except Exception:
                    tail = None
                if isinstance(tail, dict):
                    item["tail_rows"] = tail.get("rows") or []

            if row_count > (max_rows * 2):
                sample_limit = min(3, max_rows)
                try:
                    middle = await get_workspace_dataframe_rows(
                        workspace_id=workspace_id,
                        artifact_id=artifact_id,
                        offset=max(0, row_count // 2),
                        limit=sample_limit,
                    )
                except Exception:
                    middle = None
                if isinstance(middle, dict):
                    item["sample_rows"] = middle.get("rows") or []

        elif kind == "figure" and artifact_id:
            try:
                metadata = await get_workspace_artifact_metadata_via_kernel(
                    workspace_id=workspace_id,
                    artifact_id=artifact_id,
                )
            except Exception:
                metadata = None
            if isinstance(metadata, dict):
                payload = metadata.get("payload")
                if isinstance(payload, dict):
                    figure = payload.get("figure") if isinstance(payload.get("figure"), dict) else payload
                    if isinstance(figure, dict):
                        layout = figure.get("layout") if isinstance(figure.get("layout"), dict) else {}
                        data = figure.get("data") if isinstance(figure.get("data"), list) else []
                        item["figure_summary"] = {
                            "trace_count": len(data),
                            "title": str(layout.get("title") or ""),
                        }

        summary["artifacts"].append(item)

    return summary
