"""Repository helpers for filesystem-backed turn artifact metadata."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TurnArtifact


class TurnArtifactRepository:
    """CRUD helpers for turn-owned artifact metadata rows."""

    @staticmethod
    async def list_for_turn(
        session: AsyncSession,
        turn_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[TurnArtifact]:
        stmt = select(TurnArtifact).where(TurnArtifact.turn_id == turn_id)
        if not include_deleted:
            stmt = stmt.where(TurnArtifact.status != "deleted")
        result = await session.execute(stmt.order_by(TurnArtifact.created_at.asc(), TurnArtifact.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def replace_for_turn(
        session: AsyncSession,
        *,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        items: list[dict[str, object]],
    ) -> list[TurnArtifact]:
        await session.execute(delete(TurnArtifact).where(TurnArtifact.turn_id == turn_id))
        rows: list[TurnArtifact] = []
        for item in items:
            row = TurnArtifact(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                artifact_id=str(item["artifact_id"]),
                kind=str(item["kind"]),
                logical_name=str(item["logical_name"]) if item.get("logical_name") is not None else None,
                storage_path=str(item["storage_path"]),
                payload_format=str(item["payload_format"]),
                size_bytes=int(item["size_bytes"]) if item.get("size_bytes") is not None else None,
                status=str(item.get("status") or "active"),
            )
            session.add(row)
            rows.append(row)
        await session.flush()
        return rows

    @staticmethod
    async def mark_turn_for_deletion(session: AsyncSession, turn_id: str) -> None:
        rows = await TurnArtifactRepository.list_for_turn(session, turn_id, include_deleted=True)
        marked_at = datetime.now(UTC)
        for row in rows:
            row.status = "marked"
            row.deleted_at = marked_at
        await session.flush()
