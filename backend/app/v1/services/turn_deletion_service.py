"""Internal turn soft-delete helpers for future node deletion UX."""

from __future__ import annotations

from datetime import UTC, datetime

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

        children = await ConversationRepository.list_child_turns(session, conversation_id, turn.id)
        if children:
            raise HTTPException(
                status_code=409,
                detail="Turn delete is blocked because child turns would become orphaned.",
            )
        if turn.seq_no == 1 or not str(turn.parent_turn_id or "").strip():
            raise HTTPException(
                status_code=409,
                detail="Root turns cannot be deleted until branch rewiring is supported.",
            )

        marked_at = datetime.now(UTC)
        turn.is_marked_for_deletion = True
        turn.marked_for_deletion_at = marked_at
        turn.deletion_status = "marked"
        turn.deletion_error = None
        await TurnArtifactRepository.mark_turn_for_deletion(session, turn_id)
        await session.flush()
