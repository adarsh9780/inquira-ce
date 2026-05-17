from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.services.turn_deletion_service import TurnDeletionService


@pytest.mark.asyncio
async def test_mark_turn_for_deletion_marks_turn_and_artifacts(monkeypatch) -> None:
    turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        seq_no=2,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error="old error",
    )
    captured = {"artifacts_marked": False, "flushed": False}

    async def fake_get_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return turn

    async def fake_list_child_turns(session, conversation_id, parent_turn_id):
        _ = session, conversation_id, parent_turn_id
        return []

    async def fake_mark_turn_artifacts(session, turn_id):
        _ = session, turn_id
        captured["artifacts_marked"] = True

    async def fake_flush():
        captured["flushed"] = True

    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.get_turn",
        fake_get_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_child_turns",
        fake_list_child_turns,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.TurnArtifactRepository.mark_turn_for_deletion",
        fake_mark_turn_artifacts,
    )

    session = SimpleNamespace(flush=fake_flush)
    await TurnDeletionService.mark_turn_for_deletion(
        session,
        conversation_id="conversation-1",
        turn_id="turn-2",
    )

    assert turn.is_marked_for_deletion is True
    assert turn.marked_for_deletion_at is not None
    assert turn.deletion_status == "marked"
    assert turn.deletion_error is None
    assert captured["artifacts_marked"] is True
    assert captured["flushed"] is True


@pytest.mark.asyncio
async def test_mark_turn_for_deletion_blocks_root_and_branch_nodes(monkeypatch) -> None:
    root_turn = SimpleNamespace(
        id="turn-1",
        conversation_id="conversation-1",
        parent_turn_id=None,
        seq_no=1,
    )

    async def fake_get_root_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return root_turn

    async def fake_list_children(session, conversation_id, parent_turn_id):
        _ = session, conversation_id, parent_turn_id
        return []

    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.get_turn",
        fake_get_root_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_child_turns",
        fake_list_children,
    )

    with pytest.raises(Exception) as root_exc:
        await TurnDeletionService.mark_turn_for_deletion(
            SimpleNamespace(flush=lambda: None),
            conversation_id="conversation-1",
            turn_id="turn-1",
        )

    assert "Root turns cannot be deleted" in str(root_exc.value)

    branch_turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        seq_no=2,
    )

    async def fake_get_branch_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return branch_turn

    async def fake_list_branch_children(session, conversation_id, parent_turn_id):
        _ = session, conversation_id, parent_turn_id
        return [SimpleNamespace(id="turn-3")]

    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.get_turn",
        fake_get_branch_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_child_turns",
        fake_list_branch_children,
    )

    with pytest.raises(Exception) as child_exc:
        await TurnDeletionService.mark_turn_for_deletion(
            SimpleNamespace(flush=lambda: None),
            conversation_id="conversation-1",
            turn_id="turn-2",
        )

    assert "child turns would become orphaned" in str(child_exc.value)
