"""Helpers for compact branch-level turn summaries."""

from __future__ import annotations

import json
from typing import Any


class BranchSummaryService:
    """Store a compact summary of prior turns for reuse in later context assembly."""

    @staticmethod
    def merge_branch_summary(
        current_summary_json: str | None,
        *,
        turn_id: str,
        parent_turn_id: str | None,
        question: str,
        assistant_text: str,
        result_kind: str | None,
        artifacts: list[dict[str, Any]] | None,
    ) -> str:
        try:
            current = json.loads(str(current_summary_json or "") or "[]")
        except json.JSONDecodeError:
            current = []
        if not isinstance(current, list):
            current = []

        entry = {
            "turn_id": str(turn_id or ""),
            "parent_turn_id": str(parent_turn_id or "") or None,
            "question": str(question or "").strip()[:240],
            "assistant_summary": str(assistant_text or "").strip()[:320],
            "result_kind": str(result_kind or "").strip() or None,
            "artifact_count": len([item for item in (artifacts or []) if isinstance(item, dict)]),
        }
        current.append(entry)
        return json.dumps(current[-20:])
