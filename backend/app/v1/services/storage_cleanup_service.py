"""Background cleanup for soft-deleted conversations and turns."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ...data_access.coordinator import LeaseConflictError, LeaseKinds, ResourceLeaseCoordinator
from ..db.session import AppDataSessionLocal
from ..repositories.conversation_repository import ConversationRepository


SOFT_DELETE_GRACE_PERIOD = timedelta(hours=24)
SOFT_DELETE_SWEEP_INTERVAL_SECONDS = 4 * 60 * 60


class StorageCleanupService:
    """Best-effort cleanup worker for deferred filesystem and metadata removal."""

    def __init__(self) -> None:
        self._leases = ResourceLeaseCoordinator(lease_seconds=300)

    async def run_once(self) -> None:
        owner_token = f"storage-cleanup:{uuid.uuid4()}"
        async with AppDataSessionLocal() as session:
            try:
                await self._leases.acquire_system_lease(
                    session,
                    resource_key="storage_cleanup",
                    lease_kind=LeaseKinds.STORAGE_CLEANUP,
                    owner_token=owner_token,
                    metadata={"source": "storage_cleanup_service"},
                )
                await session.commit()
            except LeaseConflictError:
                await session.rollback()
                return

        try:
            cutoff = datetime.now(UTC) - SOFT_DELETE_GRACE_PERIOD
            async with AppDataSessionLocal() as session:
                conversations = await ConversationRepository.list_conversations_marked_for_deletion(
                    session,
                    marked_before=cutoff,
                )
                for conversation in conversations:
                    await self._cleanup_conversation(session, conversation)

                turns = await ConversationRepository.list_turns_marked_for_deletion(
                    session,
                    marked_before=cutoff,
                )
                for turn in turns:
                    parent_conversation = await ConversationRepository.get_conversation(
                        session,
                        str(getattr(turn, "conversation_id", "") or ""),
                        include_deleted=True,
                    )
                    if parent_conversation is not None and bool(parent_conversation.is_marked_for_deletion):
                        continue
                    await self._cleanup_turn(session, turn)
        finally:
            async with AppDataSessionLocal() as session:
                await self._leases.release_lease(
                    session,
                    resource_key="storage_cleanup",
                    lease_kind=LeaseKinds.STORAGE_CLEANUP,
                    owner_token=owner_token,
                )
                await session.commit()

    async def worker_loop(self) -> None:
        """Run cleanup immediately once, then continue periodically."""
        while True:
            try:
                await self.run_once()
                await asyncio.sleep(SOFT_DELETE_SWEEP_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(60)

    async def _cleanup_conversation(self, session, conversation) -> None:
        try:
            conversation.deletion_status = "deleting"
            conversation.deletion_error = None
            await session.commit()

            await asyncio.to_thread(self._delete_path_if_present, conversation.storage_path)
            await ConversationRepository.delete_conversation(session, conversation)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            conversation.deletion_status = "delete_failed"
            conversation.deletion_error = str(exc)[:1000]
            await session.commit()

    async def _cleanup_turn(self, session, turn) -> None:
        try:
            turn.deletion_status = "deleting"
            turn.deletion_error = None
            await session.commit()

            await asyncio.to_thread(self._delete_path_if_present, turn.storage_path)
            await session.delete(turn)
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            turn.deletion_status = "delete_failed"
            turn.deletion_error = str(exc)[:1000]
            await session.commit()

    @staticmethod
    def _delete_path_if_present(raw_path: str | None) -> None:
        if not raw_path:
            return
        path = Path(str(raw_path))
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path)
            return
        path.unlink()
