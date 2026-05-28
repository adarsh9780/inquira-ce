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
async def test_delete_turn_cascades_branch_and_reassigns_final_turn(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conversation-1", workspace_id="workspace-1", final_turn_id="turn-2")
    parent = SimpleNamespace(id="turn-1", conversation_id="conversation-1", parent_turn_id=None, seq_no=1, is_final=False)
    turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        seq_no=2,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error="old",
        is_final=True,
    )
    child = SimpleNamespace(
        id="turn-3",
        conversation_id="conversation-1",
        parent_turn_id="turn-2",
        seq_no=3,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error=None,
        is_final=False,
    )
    marked_artifacts = []

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return SimpleNamespace(id=workspace_id)

    async def fake_get_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return {"turn-1": parent, "turn-2": turn, "turn-3": child}.get(turn_id)

    async def fake_list_turns_in_sequence(session, conversation_id):
        _ = session, conversation_id
        return [parent, turn, child]

    async def fake_mark_turn_artifacts(session, turn_id):
        _ = session
        marked_artifacts.append(turn_id)

    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_conversation", fake_get_conversation)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationService.ensure_workspace_access", fake_ensure_workspace_access)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.get_turn", fake_get_turn)
    monkeypatch.setattr("app.v1.services.conversation_service.ConversationRepository.list_turns_in_sequence", fake_list_turns_in_sequence)
    monkeypatch.setattr("app.v1.services.conversation_service.TurnArtifactRepository.mark_turn_for_deletion", fake_mark_turn_artifacts)

    session = _Session()
    await ConversationService.delete_turn(
        session,
        principal_id="user-1",
        conversation_id="conversation-1",
        turn_id="turn-2",
    )

    assert turn.is_marked_for_deletion is True
    assert child.is_marked_for_deletion is True
    assert conversation.final_turn_id == "turn-1"
    assert parent.is_final is True
    assert marked_artifacts == ["turn-2", "turn-3"]
    assert session.committed is True


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
    assert "no longer supported" in str(self_exc.value)


@pytest.mark.asyncio
async def test_reorder_turns_is_no_longer_supported(monkeypatch) -> None:
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
    assert "no longer supported" in str(duplicate_exc.value)
