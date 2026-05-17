from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.storage_cleanup_service import StorageCleanupService


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.deleted = []

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def delete(self, value) -> None:
        self.deleted.append(value)


@pytest.mark.asyncio
async def test_cleanup_conversation_deletes_folder_and_row(monkeypatch, tmp_path) -> None:
    conversation_dir = tmp_path / "conversation-1"
    conversation_dir.mkdir(parents=True, exist_ok=True)
    (conversation_dir / "turns").mkdir(parents=True, exist_ok=True)
    conversation = SimpleNamespace(
        id="conversation-1",
        storage_path=str(conversation_dir),
        deletion_status="marked",
        deletion_error=None,
    )
    session = _FakeSession()
    captured = {"deleted": False}

    async def fake_delete_conversation(session_obj, conversation_obj):
        _ = session_obj, conversation_obj
        captured["deleted"] = True

    monkeypatch.setattr(
        "app.v1.services.storage_cleanup_service.ConversationRepository.delete_conversation",
        fake_delete_conversation,
    )

    service = StorageCleanupService()
    await service._cleanup_conversation(session, conversation)

    assert conversation_dir.exists() is False
    assert captured["deleted"] is True
    assert session.commits == 2
    assert conversation.deletion_status == "deleting"


@pytest.mark.asyncio
async def test_cleanup_turn_is_idempotent_when_folder_missing(tmp_path) -> None:
    missing_turn_dir = tmp_path / "missing-turn"
    turn = SimpleNamespace(
        id="turn-1",
        storage_path=str(missing_turn_dir),
        deletion_status="marked",
        deletion_error=None,
    )
    session = _FakeSession()

    service = StorageCleanupService()
    await service._cleanup_turn(session, turn)

    assert session.deleted == [turn]
    assert session.commits == 2
    assert turn.deletion_status == "deleting"


@pytest.mark.asyncio
async def test_run_once_skips_turn_cleanup_when_parent_conversation_is_marked(monkeypatch) -> None:
    due_conversation = SimpleNamespace(id="conversation-1", storage_path=None)
    due_turn = SimpleNamespace(id="turn-1", conversation_id="conversation-1", storage_path=None)

    async def fake_list_conversations(session, *, marked_before):
        _ = session, marked_before
        return [due_conversation]

    async def fake_list_turns(session, *, marked_before):
        _ = session, marked_before
        return [due_turn]

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return SimpleNamespace(is_marked_for_deletion=True)

    cleaned = {"conversation": 0, "turn": 0}

    async def fake_cleanup_conversation(session, conversation):
        _ = session, conversation
        cleaned["conversation"] += 1

    async def fake_cleanup_turn(session, turn):
        _ = session, turn
        cleaned["turn"] += 1

    class _RunSession:
        async def commit(self):
            return None

        async def rollback(self):
            return None

    class _SessionContext:
        async def __aenter__(self):
            return _RunSession()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.v1.services.storage_cleanup_service.ConversationRepository.list_conversations_marked_for_deletion",
        fake_list_conversations,
    )
    monkeypatch.setattr(
        "app.v1.services.storage_cleanup_service.ConversationRepository.list_turns_marked_for_deletion",
        fake_list_turns,
    )
    monkeypatch.setattr(
        "app.v1.services.storage_cleanup_service.ConversationRepository.get_conversation",
        fake_get_conversation,
    )
    monkeypatch.setattr(
        "app.v1.services.storage_cleanup_service.AppDataSessionLocal",
        lambda: _SessionContext(),
    )

    service = StorageCleanupService()
    monkeypatch.setattr(service, "_cleanup_conversation", fake_cleanup_conversation)
    monkeypatch.setattr(service, "_cleanup_turn", fake_cleanup_turn)

    async def fake_acquire_system_lease(*args, **kwargs):
        _ = args, kwargs
        return "cleanup-worker"

    async def fake_release_lease(*args, **kwargs):
        _ = args, kwargs

    monkeypatch.setattr(service._leases, "acquire_system_lease", fake_acquire_system_lease)
    monkeypatch.setattr(service._leases, "release_lease", fake_release_lease)

    await service.run_once()

    assert cleaned["conversation"] == 1
    assert cleaned["turn"] == 0
