from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_create_child_turn_links_parent_turn_id(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1")
    parent_turn = SimpleNamespace(id="turn-1", conversation_id="conv-1")
    captured: dict[str, object] = {}

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1")

    async def fake_get_turn(_session, _turn_id):
        return parent_turn

    async def fake_next_seq_no(_session, _conversation_id):
        return 4

    async def fake_create_turn(*, session, **kwargs):
        _ = session
        captured.update(kwargs)
        return SimpleNamespace(id="turn-4", parent_turn_id=kwargs.get("parent_turn_id"))

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.next_seq_no", fake_next_seq_no)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.create_turn", fake_create_turn)

    created = await ConversationService.create_child_turn(
        session=session,
        principal_id="principal-1",
        conversation_id="conv-1",
        parent_turn_id="turn-1",
        user_text="Use the earlier state",
        assistant_text="Created a branch turn.",
    )

    assert created.id == "turn-4"
    assert captured["conversation_id"] == "conv-1"
    assert captured["seq_no"] == 4
    assert captured["parent_turn_id"] == "turn-1"
