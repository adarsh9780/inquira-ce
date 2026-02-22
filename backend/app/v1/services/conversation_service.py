"""Conversation and paginated turn service."""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Conversation, Workspace
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .cursor_service import decode_cursor, encode_cursor


class ConversationService:
    """Business logic for conversations and turns."""

    @staticmethod
    async def ensure_workspace_access(
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
    ) -> Workspace:
        """Validate workspace ownership and return workspace."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
        title: str | None,
    ) -> Conversation:
        """Create conversation with default title fallback."""
        await ConversationService.ensure_workspace_access(session, user_id, workspace_id)
        conv_title = title.strip() if title and title.strip() else "New Conversation"
        conversation = await ConversationRepository.create_conversation(
            session,
            workspace_id,
            user_id,
            conv_title,
        )
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversations for a workspace."""
        await ConversationService.ensure_workspace_access(session, user_id, workspace_id)
        return await ConversationRepository.list_conversations(session, workspace_id, limit)

    @staticmethod
    async def clear_conversation(
        session: AsyncSession,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Delete all turns for a conversation but keep conversation row."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, user_id, conversation.workspace_id)
        await ConversationRepository.clear_conversation(session, conversation_id)
        await session.commit()

    @staticmethod
    async def delete_conversation(
        session: AsyncSession,
        user_id: str,
        conversation_id: str,
    ) -> None:
        """Delete full conversation including turns."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, user_id, conversation.workspace_id)
        await ConversationRepository.delete_conversation(session, conversation)
        await session.commit()

    @staticmethod
    async def update_conversation(
        session: AsyncSession,
        user_id: str,
        conversation_id: str,
        title: str | None,
    ) -> Conversation:
        """Update conversation title."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, user_id, conversation.workspace_id)

        if title is not None:
            new_title = title.strip() or "Untitled Conversation"
            await ConversationRepository.update_conversation(session, conversation, new_title)
            await session.commit()
            await session.refresh(conversation)

        return conversation

    @staticmethod
    async def list_turns(
        session: AsyncSession,
        user_id: str,
        conversation_id: str,
        limit: int = 5,
        before: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Return paginated turns with cursor."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, user_id, conversation.workspace_id)

        before_created_at, before_turn_id = decode_cursor(before)
        turns = await ConversationRepository.list_turns_page(
            session,
            conversation_id,
            max(1, min(limit, 50)),
            before_created_at,
            before_turn_id,
        )

        mapped: list[dict] = []
        for turn in turns:
            mapped.append(
                {
                    "id": turn.id,
                    "seq_no": turn.seq_no,
                    "user_text": turn.user_text,
                    "assistant_text": turn.assistant_text,
                    "tool_events": json.loads(turn.tool_events_json) if turn.tool_events_json else None,
                    "metadata": json.loads(turn.metadata_json) if turn.metadata_json else None,
                    "code_snapshot": turn.code_snapshot,
                    "created_at": turn.created_at,
                }
            )

        next_cursor = None
        if len(turns) == max(1, min(limit, 50)):
            last = turns[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return mapped, next_cursor
