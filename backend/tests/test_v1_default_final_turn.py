from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_persist_turn_defaults_first_saved_turn_to_final(monkeypatch) -> None:
    async def fake_next_seq_no(_session, _conversation_id):
        return 1

    created_turn = SimpleNamespace(
        id="turn-1",
        is_final=False,
        code_path=None,
        manifest_path=None,
        artifact_summary_json=None,
        execution_summary_json=None,
        schema_usage_json=None,
        parent_turn_id=None,
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
    conversation = SimpleNamespace(
        title="New Conversation",
        final_turn_id=None,
        schema_memory_json=None,
        schema_memory_version=None,
        branch_summary_json=None,
    )

    turn_id = await ChatService._persist_turn(
        session=session,
        conversation=conversation,
        username="alice",
        workspace_id="workspace-1",
        workspace_schema=None,
        data_path=None,
        conversation_id="conversation-1",
        question="Find monthly revenue",
        attachments=None,
        response_payload={
          "explanation": "Grouped revenue by month.",
          "code": "print('monthly revenue')\n",
          "artifacts": [],
          "execution": {"status": "success", "success": True},
        },
        result={},
    )

    assert turn_id == "turn-1"
    assert conversation.final_turn_id == "turn-1"
    assert created_turn.is_final is True
