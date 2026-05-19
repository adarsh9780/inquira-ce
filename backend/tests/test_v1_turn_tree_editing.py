from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.conversation_service import ConversationService


class _Session:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_delete_turn_blocks_final_turn(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conversation-1", workspace_id="workspace-1", final_turn_id="turn-2")
    turn = SimpleNamespace(id="turn-2", conversation_id="conversation-1", parent_turn_id="turn-1", seq_no=2)

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return SimpleNamespace(id=workspace_id)

    async def fake_get_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return turn

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)

    with pytest.raises(Exception) as exc:
        await ConversationService.delete_turn(
            _Session(),
            principal_id="user-1",
            conversation_id="conversation-1",
            turn_id="turn-2",
        )

    assert "Final turn cannot be deleted" in str(exc.value)


@pytest.mark.asyncio
async def test_move_turn_blocks_self_and_descendant_parent(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conversation-1", workspace_id="workspace-1")
    moving_turn = SimpleNamespace(id="turn-2", conversation_id="conversation-1", parent_turn_id="turn-1", seq_no=2)
    descendant = SimpleNamespace(id="turn-3", conversation_id="conversation-1", parent_turn_id="turn-2", seq_no=3)

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return SimpleNamespace(id=workspace_id)

    async def fake_get_turn(session, turn_id, *, include_deleted=False):
        _ = session, include_deleted
        if turn_id == "turn-2":
            return moving_turn
        if turn_id == "turn-3":
            return descendant
        return None

    async def fake_list_turns_in_sequence(session, conversation_id):
        _ = session, conversation_id
        return [
            SimpleNamespace(id="turn-1", parent_turn_id=None),
            moving_turn,
            descendant,
        ]

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_turns_in_sequence", fake_list_turns_in_sequence)

    with pytest.raises(Exception) as self_exc:
        await ConversationService.move_turn_parent(
            _Session(),
            principal_id="user-1",
            conversation_id="conversation-1",
            turn_id="turn-2",
            parent_turn_id="turn-2",
        )
    assert "under itself" in str(self_exc.value)

    with pytest.raises(Exception) as descendant_exc:
        await ConversationService.move_turn_parent(
            _Session(),
            principal_id="user-1",
            conversation_id="conversation-1",
            turn_id="turn-2",
            parent_turn_id="turn-3",
        )
    assert "under one of its descendants" in str(descendant_exc.value)


@pytest.mark.asyncio
async def test_reorder_turns_requires_exact_visible_sibling_set(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conversation-1", workspace_id="workspace-1")
    siblings = [
        SimpleNamespace(id="turn-2", sibling_order=1),
        SimpleNamespace(id="turn-3", sibling_order=2),
    ]
    session = _Session()

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return SimpleNamespace(id=workspace_id)

    async def fake_list_visible_siblings(session, conversation_id, parent_turn_id):
        _ = session, conversation_id, parent_turn_id
        return siblings

    async def fake_get_turn_tree(session, principal_id, conversation_id):
        _ = session, principal_id, conversation_id
        return {"roots": [], "current_turn_id": None, "final_turn_id": None}

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_visible_siblings", fake_list_visible_siblings)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.get_turn_tree", fake_get_turn_tree)

    with pytest.raises(Exception) as duplicate_exc:
        await ConversationService.reorder_turns(
            session,
            principal_id="user-1",
            conversation_id="conversation-1",
            parent_turn_id="turn-1",
            turn_ids=["turn-2", "turn-2"],
        )
    assert "duplicate" in str(duplicate_exc.value)

    with pytest.raises(Exception) as missing_exc:
        await ConversationService.reorder_turns(
            session,
            principal_id="user-1",
            conversation_id="conversation-1",
            parent_turn_id="turn-1",
            turn_ids=["turn-2"],
        )
    assert "exactly the visible siblings" in str(missing_exc.value)

    await ConversationService.reorder_turns(
        session,
        principal_id="user-1",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        turn_ids=["turn-3", "turn-2"],
    )

    assert siblings[1].sibling_order == 1
    assert siblings[0].sibling_order == 2
    assert session.committed is True
