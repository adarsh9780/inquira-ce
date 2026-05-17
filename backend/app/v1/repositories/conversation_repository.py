"""Repository methods for conversation and turn persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Conversation, Turn


class ConversationRepository:
    """Conversation/turn DB abstraction."""

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        workspace_id: str,
        principal_id: str,
        title: str,
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(
            workspace_id=workspace_id,
            created_by_principal_id=principal_id,
            title=title,
        )
        session.add(conv)
        await session.flush()
        return conv

    @staticmethod
    async def list_conversations(session: AsyncSession, workspace_id: str, limit: int = 50) -> list[Conversation]:
        """List conversations by recency."""
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.is_marked_for_deletion.is_(False),
            )
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def count_for_workspace(session: AsyncSession, workspace_id: str) -> int:
        """Count conversations stored for one workspace."""
        result = await session.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.workspace_id == workspace_id,
                Conversation.is_marked_for_deletion.is_(False),
            )
        )
        return int(result.scalar_one() or 0)

    @staticmethod
    async def get_conversation(
        session: AsyncSession,
        conversation_id: str,
        *,
        include_deleted: bool = False,
    ) -> Conversation | None:
        """Get conversation by id."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if not include_deleted:
            stmt = stmt.where(Conversation.is_marked_for_deletion.is_(False))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_turn(
        session: AsyncSession,
        turn_id: str,
        *,
        include_deleted: bool = False,
    ) -> Turn | None:
        """Get turn by id."""
        stmt = select(Turn).where(Turn.id == turn_id)
        if not include_deleted:
            stmt = stmt.where(Turn.is_marked_for_deletion.is_(False))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_child_turns(session: AsyncSession, conversation_id: str, parent_turn_id: str) -> list[Turn]:
        """List direct child turns in sequence order."""
        result = await session.execute(
            select(Turn)
            .where(
                Turn.conversation_id == conversation_id,
                Turn.parent_turn_id == parent_turn_id,
                Turn.is_marked_for_deletion.is_(False),
            )
            .order_by(Turn.seq_no.asc(), Turn.created_at.asc(), Turn.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_turns_in_sequence(session: AsyncSession, conversation_id: str) -> list[Turn]:
        """List turns oldest-first for migration and lineage rebuilds."""
        result = await session.execute(
            select(Turn)
            .where(
                Turn.conversation_id == conversation_id,
                Turn.is_marked_for_deletion.is_(False),
            )
            .order_by(Turn.seq_no.asc(), Turn.created_at.asc(), Turn.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_conversation(session: AsyncSession, conversation: Conversation) -> None:
        """Delete conversation and cascaded turns."""
        await session.delete(conversation)

    @staticmethod
    async def list_conversations_marked_for_deletion(
        session: AsyncSession,
        *,
        marked_before: datetime,
    ) -> list[Conversation]:
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.is_marked_for_deletion.is_(True),
                Conversation.marked_for_deletion_at.is_not(None),
                Conversation.marked_for_deletion_at <= marked_before,
            )
            .order_by(Conversation.marked_for_deletion_at.asc(), Conversation.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_conversations_needing_migration(
        session: AsyncSession,
        *,
        target_version: int,
        limit: int = 100,
    ) -> list[Conversation]:
        result = await session.execute(
            select(Conversation)
            .where(
                Conversation.is_marked_for_deletion.is_(False),
                ((Conversation.migration_version.is_(None)) | (Conversation.migration_version < target_version)),
            )
            .order_by(Conversation.created_at.asc(), Conversation.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_turns_marked_for_deletion(
        session: AsyncSession,
        *,
        marked_before: datetime,
    ) -> list[Turn]:
        result = await session.execute(
            select(Turn)
            .where(
                Turn.is_marked_for_deletion.is_(True),
                Turn.marked_for_deletion_at.is_not(None),
                Turn.marked_for_deletion_at <= marked_before,
            )
            .order_by(Turn.marked_for_deletion_at.asc(), Turn.id.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def mark_conversation_for_deletion(session: AsyncSession, conversation: Conversation) -> None:
        """Soft-delete a conversation and its turns."""
        marked_at = datetime.now(UTC)
        conversation.is_marked_for_deletion = True
        conversation.marked_for_deletion_at = marked_at
        conversation.deletion_status = "marked"
        conversation.deletion_error = None

        result = await session.execute(
            select(Turn).where(Turn.conversation_id == conversation.id)
        )
        for turn in result.scalars().all():
            turn.is_marked_for_deletion = True
            turn.marked_for_deletion_at = marked_at
            turn.deletion_status = "marked"
            turn.deletion_error = None
        await session.flush()

    @staticmethod
    async def update_conversation(session: AsyncSession, conversation: Conversation, title: str) -> None:
        """Update conversation title."""
        conversation.title = title
        await session.flush()

    @staticmethod
    async def clear_conversation(session: AsyncSession, conversation_id: str) -> None:
        """Delete all turns for a conversation."""
        await session.execute(delete(Turn).where(Turn.conversation_id == conversation_id))

    @staticmethod
    async def next_seq_no(session: AsyncSession, conversation_id: str) -> int:
        """Return next sequence number for a conversation turn."""
        result = await session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(next_turn_seq=Conversation.next_turn_seq + 1)
            .returning(Conversation.next_turn_seq)
        )
        next_value = result.scalar_one_or_none()
        if next_value is None:
            raise ValueError(f"Conversation not found for seq allocation: {conversation_id}")
        return max(1, int(next_value) - 1)

    @staticmethod
    async def create_turn(
        session: AsyncSession,
        conversation_id: str,
        seq_no: int,
        user_text: str,
        assistant_text: str,
        tool_events: list[dict] | None,
        metadata: dict | None,
        code_snapshot: str | None,
        parent_turn_id: str | None = None,
    ) -> Turn:
        """Create and persist one turn."""
        turn = Turn(
            conversation_id=conversation_id,
            parent_turn_id=parent_turn_id,
            seq_no=seq_no,
            user_text=user_text,
            assistant_text=assistant_text,
            tool_events_json=json.dumps(tool_events) if tool_events is not None else None,
            metadata_json=json.dumps(metadata) if metadata is not None else None,
            code_snapshot=code_snapshot,
        )
        session.add(turn)

        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation:
            conversation.last_turn_at = datetime.now(UTC)

        await session.flush()
        return turn

    @staticmethod
    async def list_turns_page(
        session: AsyncSession,
        conversation_id: str,
        limit: int,
        before_created_at: datetime | None,
        before_turn_id: str | None,
    ) -> list[Turn]:
        """List turns newest-first with optional cursor boundary."""
        stmt = (
            select(Turn)
            .where(
                Turn.conversation_id == conversation_id,
                Turn.is_marked_for_deletion.is_(False),
            )
            .order_by(desc(Turn.created_at), desc(Turn.id))
            .limit(limit)
        )
        if before_created_at is not None and before_turn_id is not None:
            stmt = stmt.where(
                (Turn.created_at < before_created_at)
                | ((Turn.created_at == before_created_at) & (Turn.id < before_turn_id))
            )
        result = await session.execute(stmt)
        return list(result.scalars().all())
