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

    async def fake_list_turns_in_sequence(session, conversation_id):
        _ = session, conversation_id
        return [turn]

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
        "app.v1.services.turn_deletion_service.ConversationRepository.list_turns_in_sequence",
        fake_list_turns_in_sequence,
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
async def test_mark_turn_for_deletion_cascades_root_and_branch_nodes(monkeypatch) -> None:
    root_turn = SimpleNamespace(
        id="turn-1",
        conversation_id="conversation-1",
        parent_turn_id=None,
        seq_no=1,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error=None,
    )
    child_turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        seq_no=2,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error=None,
    )
    marked_artifacts = []

    async def fake_get_root_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return root_turn

    async def fake_list_children(session, conversation_id, parent_turn_id):
        _ = session, conversation_id, parent_turn_id
        return []

    async def fake_list_turns_in_sequence(session, conversation_id):
        _ = session, conversation_id
        return [root_turn, child_turn]

    async def fake_mark_turn_artifacts(session, turn_id):
        _ = session
        marked_artifacts.append(turn_id)

    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.get_turn",
        fake_get_root_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_child_turns",
        fake_list_children,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_turns_in_sequence",
        fake_list_turns_in_sequence,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.TurnArtifactRepository.mark_turn_for_deletion",
        fake_mark_turn_artifacts,
    )

    async def fake_flush():
        return None

    await TurnDeletionService.mark_turn_for_deletion(
        SimpleNamespace(flush=fake_flush),
        conversation_id="conversation-1",
        turn_id="turn-1",
    )

    assert root_turn.is_marked_for_deletion is True
    assert child_turn.is_marked_for_deletion is True
    assert marked_artifacts == ["turn-1", "turn-2"]

    branch_turn = SimpleNamespace(
        id="turn-2",
        conversation_id="conversation-1",
        parent_turn_id="turn-1",
        seq_no=2,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error=None,
    )

    async def fake_get_branch_turn(session, turn_id, *, include_deleted=False):
        _ = session, turn_id, include_deleted
        return branch_turn

    grandchild_turn = SimpleNamespace(
        id="turn-3",
        conversation_id="conversation-1",
        parent_turn_id="turn-2",
        seq_no=3,
        is_marked_for_deletion=False,
        marked_for_deletion_at=None,
        deletion_status="active",
        deletion_error=None,
    )

    async def fake_list_branch_turns_in_sequence(session, conversation_id):
        _ = session, conversation_id
        return [root_turn, branch_turn, grandchild_turn]

    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.get_turn",
        fake_get_branch_turn,
    )
    monkeypatch.setattr(
        "app.v1.services.turn_deletion_service.ConversationRepository.list_turns_in_sequence",
        fake_list_branch_turns_in_sequence,
    )

    await TurnDeletionService.mark_turn_for_deletion(
        SimpleNamespace(flush=fake_flush),
        conversation_id="conversation-1",
        turn_id="turn-2",
    )

    assert branch_turn.is_marked_for_deletion is True
    assert grandchild_turn.is_marked_for_deletion is True
