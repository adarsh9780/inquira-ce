"""Conversation and paginated turn service."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Conversation, Turn, Workspace
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .cursor_service import decode_cursor, encode_cursor


class ConversationService:
    """Business logic for conversations and turns."""

    @staticmethod
    def _has_turn_bundle(turn: Turn) -> bool:
        code_path = str(getattr(turn, "code_path", "") or "").strip()
        manifest_path = str(getattr(turn, "manifest_path", "") or "").strip()
        if not code_path or not manifest_path:
            return False
        return Path(code_path).is_file() and Path(manifest_path).is_file()

    @staticmethod
    def _turn_to_dict(turn: Turn) -> dict:
        return {
            "id": turn.id,
            "parent_turn_id": turn.parent_turn_id,
            "result_kind": turn.result_kind,
            "code_path": turn.code_path,
            "manifest_path": turn.manifest_path,
            "seq_no": turn.seq_no,
            "user_text": turn.user_text,
            "assistant_text": turn.assistant_text,
            "tool_events": json.loads(turn.tool_events_json) if turn.tool_events_json else None,
            "metadata": json.loads(turn.metadata_json) if turn.metadata_json else None,
            "code_snapshot": turn.code_snapshot,
            "created_at": turn.created_at,
        }

    @staticmethod
    async def ensure_workspace_access(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ) -> Workspace:
        """Validate workspace ownership and return workspace."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    @staticmethod
    async def create_conversation(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        title: str | None,
    ) -> Conversation:
        """Create conversation with default title fallback."""
        await ConversationService.ensure_workspace_access(session, principal_id, workspace_id)
        conv_title = title.strip() if title and title.strip() else "New Conversation"
        conversation = await ConversationRepository.create_conversation(
            session,
            workspace_id,
            principal_id,
            conv_title,
        )
        await session.commit()
        await session.refresh(conversation)
        return conversation

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversations for a workspace."""
        await ConversationService.ensure_workspace_access(session, principal_id, workspace_id)
        return await ConversationRepository.list_conversations(session, workspace_id, limit)

    @staticmethod
    async def clear_conversation(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
    ) -> None:
        """Delete all turns for a conversation but keep conversation row."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        await ConversationRepository.clear_conversation(session, conversation_id)
        await session.commit()

    @staticmethod
    async def delete_conversation(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
    ) -> None:
        """Delete full conversation including turns."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        await ConversationRepository.delete_conversation(session, conversation)
        await session.commit()

    @staticmethod
    async def update_conversation(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        title: str | None,
    ) -> Conversation:
        """Update conversation title."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

        if title is not None:
            new_title = title.strip() or "Untitled Conversation"
            await ConversationRepository.update_conversation(session, conversation, new_title)
            await session.commit()
            await session.refresh(conversation)

        return conversation

    @staticmethod
    async def list_turns(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        limit: int = 5,
        before: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Return paginated turns with cursor."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

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
            mapped.append(ConversationService._turn_to_dict(turn))

        next_cursor = None
        if len(turns) == max(1, min(limit, 50)):
            last = turns[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return mapped, next_cursor

    @staticmethod
    async def get_turn(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        turn_id: str,
    ) -> dict:
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        turn = await ConversationRepository.get_turn(session, turn_id)
        if turn is None or turn.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Turn not found")
        return ConversationService._turn_to_dict(turn)

    @staticmethod
    async def get_turn_relations(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        turn_id: str,
    ) -> dict:
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

        current_turn = await ConversationRepository.get_turn(session, turn_id)
        if current_turn is None or current_turn.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Turn not found")

        parent = None
        if current_turn.parent_turn_id:
            parent_turn = await ConversationRepository.get_turn(session, current_turn.parent_turn_id)
            if parent_turn is not None and parent_turn.conversation_id == conversation_id:
                parent = ConversationService._turn_to_dict(parent_turn)

        children = [
            ConversationService._turn_to_dict(turn)
            for turn in await ConversationRepository.list_child_turns(session, conversation_id, current_turn.id)
        ]
        next_turn = children[0] if children else None

        final_turn = None
        final_turn_id = str(getattr(conversation, "final_turn_id", "") or "").strip()
        if final_turn_id:
            turn = await ConversationRepository.get_turn(session, final_turn_id)
            if turn is not None and turn.conversation_id == conversation_id:
                final_turn = ConversationService._turn_to_dict(turn)

        return {
            "current": ConversationService._turn_to_dict(current_turn),
            "parent": parent,
            "children": children,
            "previous_turn": parent,
            "next_turn": next_turn,
            "final_turn": final_turn,
        }

    @staticmethod
    async def get_final_turn(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
    ) -> dict | None:
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        final_turn_id = str(getattr(conversation, "final_turn_id", "") or "").strip()
        if not final_turn_id:
            return None
        turn = await ConversationRepository.get_turn(session, final_turn_id)
        if turn is None or turn.conversation_id != conversation_id:
            return None
        return ConversationService._turn_to_dict(turn)

    @staticmethod
    async def mark_final_turn(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        turn_id: str,
    ) -> dict:
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

        turn = await ConversationRepository.get_turn(session, turn_id)
        if turn is None or turn.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Turn not found")

        try:
            execution_summary = json.loads(turn.execution_summary_json) if turn.execution_summary_json else {}
        except json.JSONDecodeError:
            execution_summary = {}
        success = bool(execution_summary.get("success")) or str(execution_summary.get("status") or "").lower() == "success"
        if not success:
            raise HTTPException(status_code=400, detail="Only successful turns can be marked final")
        if not ConversationService._has_turn_bundle(turn):
            raise HTTPException(status_code=400, detail="Only persisted turn bundles can be marked final")

        previous_final_id = str(getattr(conversation, "final_turn_id", "") or "").strip()
        if previous_final_id and previous_final_id != turn.id:
            previous_turn = await ConversationRepository.get_turn(session, previous_final_id)
            if previous_turn is not None and previous_turn.conversation_id == conversation_id:
                previous_turn.is_final = False

        turn.is_final = True
        conversation.final_turn_id = turn.id
        await session.commit()
        return ConversationService._turn_to_dict(turn)

    @staticmethod
    async def create_root_turn(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        user_text: str,
        assistant_text: str,
        *,
        tool_events: list[dict] | None = None,
        metadata: dict | None = None,
        code_snapshot: str | None = None,
    ) -> Turn:
        """Create a new root turn without a parent pointer."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
        turn = await ConversationRepository.create_turn(
            session=session,
            conversation_id=conversation_id,
            seq_no=seq_no,
            user_text=user_text,
            assistant_text=assistant_text,
            tool_events=tool_events,
            metadata=metadata,
            code_snapshot=code_snapshot,
            parent_turn_id=None,
        )
        await session.commit()
        return turn

    @staticmethod
    async def create_child_turn(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        parent_turn_id: str,
        user_text: str,
        assistant_text: str,
        *,
        tool_events: list[dict] | None = None,
        metadata: dict | None = None,
        code_snapshot: str | None = None,
    ) -> Turn:
        """Create a child turn linked to a selected parent turn."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

        parent_turn = await ConversationRepository.get_turn(session, parent_turn_id)
        if parent_turn is None or parent_turn.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Parent turn not found")

        seq_no = await ConversationRepository.next_seq_no(session, conversation_id)
        turn = await ConversationRepository.create_turn(
            session=session,
            conversation_id=conversation_id,
            seq_no=seq_no,
            user_text=user_text,
            assistant_text=assistant_text,
            tool_events=tool_events,
            metadata=metadata,
            code_snapshot=code_snapshot,
            parent_turn_id=parent_turn_id,
        )
        await session.commit()
        return turn
