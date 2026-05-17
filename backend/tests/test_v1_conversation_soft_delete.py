from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1.db.base import AppDataBase
from app.v1.models import Conversation, Principal, Turn, Workspace
from app.v1.repositories.conversation_repository import ConversationRepository
from app.v1.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_conversation_repository_hides_soft_deleted_rows(tmp_path) -> None:
    db_path = tmp_path / "appdata.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(AppDataBase.metadata.create_all)

        async with session_factory() as session:
            principal = Principal(id="principal-1", username_cached="alice", plan_cached="FREE")
            workspace = Workspace(
                id="workspace-1",
                owner_principal_id="principal-1",
                name="Workspace",
                name_normalized="workspace",
                is_active=1,
                duckdb_path="/tmp/workspace.db",
            )
            visible = Conversation(
                id="conversation-visible",
                workspace_id="workspace-1",
                title="Visible",
                created_by_principal_id="principal-1",
            )
            deleted = Conversation(
                id="conversation-deleted",
                workspace_id="workspace-1",
                title="Deleted",
                created_by_principal_id="principal-1",
                is_marked_for_deletion=True,
                deletion_status="marked",
            )
            turn_visible = Turn(
                id="turn-visible",
                conversation_id="conversation-visible",
                seq_no=1,
                user_text="hello",
                assistant_text="world",
            )
            turn_deleted = Turn(
                id="turn-deleted",
                conversation_id="conversation-visible",
                seq_no=2,
                user_text="hidden",
                assistant_text="gone",
                is_marked_for_deletion=True,
                deletion_status="marked",
            )
            session.add_all([principal, workspace, visible, deleted, turn_visible, turn_deleted])
            await session.commit()

            conversations = await ConversationRepository.list_conversations(session, "workspace-1", 50)
            visible_conversation = await ConversationRepository.get_conversation(session, "conversation-visible")
            hidden_conversation = await ConversationRepository.get_conversation(session, "conversation-deleted")
            hidden_conversation_including_deleted = await ConversationRepository.get_conversation(
                session,
                "conversation-deleted",
                include_deleted=True,
            )
            visible_turn = await ConversationRepository.get_turn(session, "turn-visible")
            hidden_turn = await ConversationRepository.get_turn(session, "turn-deleted")
            turns_page = await ConversationRepository.list_turns_page(
                session,
                "conversation-visible",
                10,
                None,
                None,
            )

            assert [item.id for item in conversations] == ["conversation-visible"]
            assert visible_conversation is not None
            assert hidden_conversation is None
            assert hidden_conversation_including_deleted is not None
            assert visible_turn is not None
            assert hidden_turn is None
            assert [item.id for item in turns_page] == ["turn-visible"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_conversation_marks_conversation_and_turns(monkeypatch) -> None:
    conversation = SimpleNamespace(
        id="conversation-1",
        workspace_id="workspace-1",
        is_marked_for_deletion=False,
    )
    captured = {"marked": False, "committed": False}

    async def fake_get_conversation(session, conversation_id, *, include_deleted=False):
        _ = session, conversation_id, include_deleted
        return conversation

    async def fake_ensure_workspace_access(session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return SimpleNamespace(id=workspace_id)

    async def fake_mark_for_deletion(session, conversation_obj):
        _ = session
        assert conversation_obj is conversation
        captured["marked"] = True
        conversation.is_marked_for_deletion = True

    async def fake_commit():
        captured["committed"] = True

    monkeypatch.setattr(
        "app.v1.services.conversation_service.ConversationRepository.get_conversation",
        fake_get_conversation,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_service.ConversationService.ensure_workspace_access",
        fake_ensure_workspace_access,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_service.ConversationRepository.mark_conversation_for_deletion",
        fake_mark_for_deletion,
    )

    session = SimpleNamespace(commit=fake_commit)
    await ConversationService.delete_conversation(session, "principal-1", "conversation-1")

    assert captured["marked"] is True
    assert captured["committed"] is True
