from __future__ import annotations

import json

import pytest

from app.v1.services.turn_bundle_service import TurnBundleService


@pytest.mark.asyncio
async def test_create_turn_bundle_writes_expected_files() -> None:
    turn_dir = await TurnBundleService.create_turn_bundle(
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        user_text="Show revenue by month",
        assistant_text="I grouped the data by month.",
        code="print('hello')\n",
        manifest={"status": "draft"},
    )

    assert turn_dir.name == "turn-1"
    assert turn_dir.joinpath("artifacts").is_dir()
    assert turn_dir.joinpath("user.md").read_text(encoding="utf-8") == "Show revenue by month"
    assert turn_dir.joinpath("assistant.md").read_text(encoding="utf-8") == "I grouped the data by month."
    assert turn_dir.joinpath("analysis.py").read_text(encoding="utf-8") == "print('hello')\n"

    manifest = json.loads(turn_dir.joinpath("turn.json").read_text(encoding="utf-8"))
    assert manifest["turn_id"] == "turn-1"
    assert manifest["conversation_id"] == "conversation-1"
    assert manifest["workspace_id"] == "workspace-1"
    assert manifest["status"] == "draft"
    assert manifest["files"]["analysis_code"] == "analysis.py"
