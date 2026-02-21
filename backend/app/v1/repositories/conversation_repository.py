"""Repository methods for conversation and turn persistence."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Conversation, Turn


class ConversationRepository:
    """Conversation/turn DB abstraction."""

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        workspace_id: str,
        user_id: str,
        title: str,
    ) -> Conversation:
        """Create a new conversation."""
        conv = Conversation(workspace_id=workspace_id, created_by_user_id=user_id, title=title)
        session.add(conv)
        await session.flush()
        return conv

    @staticmethod
    async def list_conversations(session: AsyncSession, workspace_id: str, limit: int = 50) -> list[Conversation]:
        """List conversations by recency."""
        result = await session.execute(
            select(Conversation)
            .where(Conversation.workspace_id == workspace_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_conversation(session: AsyncSession, conversation_id: str) -> Conversation | None:
        """Get conversation by id."""
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_conversation(session: AsyncSession, conversation: Conversation) -> None:
        """Delete conversation and cascaded turns."""
        await session.delete(conversation)

    @staticmethod
    async def clear_conversation(session: AsyncSession, conversation_id: str) -> None:
        """Delete all turns for a conversation."""
        await session.execute(delete(Turn).where(Turn.conversation_id == conversation_id))

    @staticmethod
    async def next_seq_no(session: AsyncSession, conversation_id: str) -> int:
        """Return next sequence number for a conversation turn."""
        result = await session.execute(
            select(Turn.seq_no)
            .where(Turn.conversation_id == conversation_id)
            .order_by(desc(Turn.seq_no))
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        return (latest or 0) + 1

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
    ) -> Turn:
        """Create and persist one turn."""
        turn = Turn(
            conversation_id=conversation_id,
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
            conversation.last_turn_at = datetime.utcnow()

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
            .where(Turn.conversation_id == conversation_id)
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
