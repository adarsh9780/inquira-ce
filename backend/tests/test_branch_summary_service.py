from __future__ import annotations

import json

from app.v1.services.branch_summary_service import BranchSummaryService


def test_branch_summary_service_appends_compact_turn_entries() -> None:
    current_summary = json.dumps(
        [
            {
                "turn_id": "turn-1",
                "parent_turn_id": None,
                "question": "Initial question",
                "assistant_summary": "Initial answer",
                "result_kind": "dataframe",
                "artifact_count": 1,
            }
        ]
    )

    merged_json = BranchSummaryService.merge_branch_summary(
        current_summary,
        turn_id="turn-2",
        parent_turn_id="turn-1",
        question="Compare it by month",
        assistant_text="I compared the same metric by month and plotted the trend.",
        result_kind="figure",
        artifacts=[{"artifact_id": "fig-1"}, {"artifact_id": "df-2"}],
    )
    merged = json.loads(merged_json)

    assert len(merged) == 2
    assert merged[-1]["turn_id"] == "turn-2"
    assert merged[-1]["parent_turn_id"] == "turn-1"
    assert merged[-1]["question"] == "Compare it by month"
    assert merged[-1]["result_kind"] == "figure"
    assert merged[-1]["artifact_count"] == 2
