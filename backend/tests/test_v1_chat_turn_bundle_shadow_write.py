from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_persist_turn_shadow_writes_turn_bundle(monkeypatch) -> None:
    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    created_turn = SimpleNamespace(
        id="turn-1",
        code_path=None,
        manifest_path=None,
        artifact_summary_json=None,
        execution_summary_json=None,
    )

    async def fake_create_turn(*, session, **kwargs):
        _ = session, kwargs
        return created_turn

    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.chat_service.ConversationRepository.create_turn", fake_create_turn)

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit
    conversation = SimpleNamespace(title="New Conversation")

    turn_id = await ChatService._persist_turn(
        session=session,
        conversation=conversation,
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        question="Find monthly revenue",
        attachments=None,
        response_payload={
            "explanation": "Grouped revenue by month.",
            "code": "print('monthly revenue')\n",
            "artifacts": [{"artifact_id": "df-1", "kind": "dataframe", "path": "artifacts/df-1.parquet"}],
            "execution": {"status": "success", "success": True},
        },
        result={},
    )

    assert turn_id == "turn-1"
    turn_dir = (
        Path.home()
        / ".inquira"
        / "alice"
        / "workspaces"
        / "workspace-1"
        / "conversations"
        / "conversation-1"
        / "turns"
        / "turn-1"
    )
    assert turn_dir.joinpath("analysis.py").read_text(encoding="utf-8") == "print('monthly revenue')\n"
    assert turn_dir.joinpath("assistant.md").read_text(encoding="utf-8") == "Grouped revenue by month."
    manifest = json.loads(turn_dir.joinpath("turn.json").read_text(encoding="utf-8"))
    assert manifest["seq_no"] == 1
    assert manifest["artifacts"][0]["artifact_id"] == "df-1"
    assert created_turn.code_path == str(turn_dir / "analysis.py")
    assert created_turn.manifest_path == str(turn_dir / "turn.json")
    assert json.loads(created_turn.artifact_summary_json)[0]["kind"] == "dataframe"
    assert json.loads(created_turn.execution_summary_json)["success"] is True
