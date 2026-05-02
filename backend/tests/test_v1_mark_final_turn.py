from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_mark_final_turn_clears_previous_final(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", final_turn_id="turn-1")
    previous_turn = SimpleNamespace(id="turn-1", conversation_id="conv-1", is_final=True, execution_summary_json='{"success": true}')
    current_turn = SimpleNamespace(id="turn-2", conversation_id="conv-1", is_final=False, execution_summary_json='{"success": true}', parent_turn_id="turn-1", result_kind="dataframe", code_path=None, manifest_path=None, seq_no=2, user_text="q", assistant_text="a", tool_events_json=None, metadata_json=None, code_snapshot="print(2)", created_at="2026-05-02T10:00:00Z")

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1")

    async def fake_get_turn(_session, turn_id):
        if turn_id == "turn-1":
            return previous_turn
        if turn_id == "turn-2":
            return current_turn
        return None

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)

    result = await ConversationService.mark_final_turn(
        session=session,
        principal_id="principal-1",
        conversation_id="conv-1",
        turn_id="turn-2",
    )

    assert result["id"] == "turn-2"
    assert conversation.final_turn_id == "turn-2"
    assert previous_turn.is_final is False
    assert current_turn.is_final is True
