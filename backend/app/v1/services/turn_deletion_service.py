"""Internal turn soft-delete helpers for future node deletion UX."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.conversation_repository import ConversationRepository
from ..repositories.turn_artifact_repository import TurnArtifactRepository


class TurnDeletionService:
    """Mark one turn and its owned artifacts for deferred cleanup."""

    @staticmethod
    async def mark_turn_for_deletion(
        session: AsyncSession,
        *,
        conversation_id: str,
        turn_id: str,
    ) -> None:
        turn = await ConversationRepository.get_turn(session, turn_id, include_deleted=True)
        if turn is None or turn.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Turn not found")

        all_turns = await ConversationRepository.list_turns_in_sequence(session, conversation_id)
        children_by_parent: dict[str, list[Any]] = {}
        for item in all_turns:
            parent_id = str(getattr(item, "parent_turn_id", "") or "").strip()
            if parent_id:
                children_by_parent.setdefault(parent_id, []).append(item)
        subtree_ids: set[str] = set()
        stack = [turn]
        while stack:
            current = stack.pop()
            current_id = str(getattr(current, "id", "") or "").strip()
            if not current_id or current_id in subtree_ids:
                continue
            subtree_ids.add(current_id)
            stack.extend(children_by_parent.get(current_id, []))
        marked_at = datetime.now(UTC)
        for item in all_turns:
            if item.id not in subtree_ids:
                continue
            item.is_marked_for_deletion = True
            item.marked_for_deletion_at = marked_at
            item.deletion_status = "marked"
            item.deletion_error = None
            await TurnArtifactRepository.mark_turn_for_deletion(session, item.id)
        await session.flush()
