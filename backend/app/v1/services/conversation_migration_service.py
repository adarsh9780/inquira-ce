"""Helpers to backfill legacy conversations into the turn-tree bundle model."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import AppDataSessionLocal
from ..models import Turn
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.principal_repository import PrincipalRepository
from ..repositories.turn_artifact_repository import TurnArtifactRepository
from .conversation_service import ConversationService
from .turn_artifact_storage_service import TurnArtifactStorageService
from .turn_bundle_service import TurnBundleService
from .workspace_maintenance_service import WorkspaceMaintenanceService


class ConversationMigrationService:
    """Backfill older linear conversations into the new turn-based structure."""

    CURRENT_MIGRATION_VERSION = 2

    @staticmethod
    def _safe_json(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _artifact_summary(turn: Turn) -> list[dict[str, str]]:
        if turn.artifact_summary_json:
            try:
                payload = json.loads(turn.artifact_summary_json)
                if isinstance(payload, list):
                    return [
                        {
                            "artifact_id": str(item.get("artifact_id") or ""),
                            "kind": str(item.get("kind") or ""),
                            "path": str(item.get("path") or ""),
                        }
                        for item in payload
                        if isinstance(item, dict)
                    ]
            except json.JSONDecodeError:
                pass

        metadata = ConversationMigrationService._safe_json(turn.metadata_json)
        raw_artifacts = metadata.get("artifacts")
        if not isinstance(raw_artifacts, list):
            return []
        return [
            {
                "artifact_id": str(item.get("artifact_id") or ""),
                "kind": str(item.get("kind") or ""),
                "path": str(item.get("path") or ""),
            }
            for item in raw_artifacts
            if isinstance(item, dict)
        ]

    @staticmethod
    async def migrate_pending_conversations_once(limit: int = 100) -> None:
        """Backfill conversations that still predate the storage migration version."""
        async with AppDataSessionLocal() as session:
            conversations = await ConversationRepository.list_conversations_needing_migration(
                session,
                target_version=ConversationMigrationService.CURRENT_MIGRATION_VERSION,
                limit=limit,
            )
            for conversation in conversations:
                principal = await PrincipalRepository.get_by_id(session, conversation.created_by_principal_id)
                if principal is None:
                    continue
                await ConversationMigrationService.migrate_conversation(
                    session=session,
                    principal_id=principal.id,
                    conversation_id=conversation.id,
                    username=principal.username_cached,
                )

    @staticmethod
    async def migrate_conversation(
        session: AsyncSession,
        principal_id: str,
        conversation_id: str,
        *,
        username: str,
    ) -> dict[str, Any]:
        """Backfill bundle files and linear lineage for one legacy conversation."""
        conversation = await ConversationRepository.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        workspace = await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)
        await TurnBundleService.create_or_update_conversation_bundle(
            username=username,
            workspace_id=conversation.workspace_id,
            conversation_id=conversation.id,
            manifest={"title": str(getattr(conversation, "title", "") or "")},
        )
        conversation.storage_path = str(
            TurnBundleService.build_conversation_dir(username, conversation.workspace_id, conversation.id)
        )

        turns = await ConversationRepository.list_turns_in_sequence(session, conversation_id)
        previous_turn: Turn | None = None
        migrated_turn_ids: list[str] = []
        maintenance_owner_token = ""
        maintenance_acquired = False

        try:
            for turn in turns:
                if previous_turn is not None and not str(turn.parent_turn_id or "").strip():
                    turn.parent_turn_id = previous_turn.id

                artifact_summary = ConversationMigrationService._artifact_summary(turn)
                manifest: dict[str, Any] = {
                    "seq_no": turn.seq_no,
                    "parent_turn_id": turn.parent_turn_id,
                    "result_kind": str(turn.result_kind or ""),
                    "artifacts": artifact_summary,
                }
                if turn.execution_summary_json:
                    manifest["execution"] = ConversationMigrationService._safe_json(turn.execution_summary_json)

                existing_artifact_rows = await TurnArtifactRepository.list_for_turn(
                    session,
                    turn.id,
                    include_deleted=True,
                )
                if artifact_summary and not existing_artifact_rows:
                    resolvable_artifacts = [
                        item for item in artifact_summary if str(item.get("artifact_id") or "").strip()
                    ]
                    if resolvable_artifacts and str(getattr(workspace, "duckdb_path", "") or "").strip():
                        if not maintenance_acquired:
                            maintenance_owner_token = (
                                f"conversation-migration:{conversation.workspace_id}:{conversation.id}:{uuid.uuid4()}"
                            )
                            try:
                                await WorkspaceMaintenanceService.acquire_lease_or_raise(
                                    session,
                                    workspace_id=str(conversation.workspace_id),
                                    owner_token=maintenance_owner_token,
                                    requested_operation="conversation_migration",
                                    metadata={"source": "conversation_migration"},
                                )
                                maintenance_acquired = True
                            except HTTPException as exc:
                                if isinstance(exc.detail, dict) and exc.detail.get("code") == "workspace_busy":
                                    artifact_summary = [
                                        {
                                            **item,
                                            "status": "legacy_orphan",
                                        }
                                        for item in artifact_summary
                                    ]
                                    resolvable_artifacts = []
                                else:
                                    raise
                    if resolvable_artifacts and str(getattr(workspace, "duckdb_path", "") or "").strip():
                        persisted_artifacts = await TurnArtifactStorageService.persist_turn_artifacts(
                            session=session,
                            username=username,
                            workspace_id=conversation.workspace_id,
                            conversation_id=conversation.id,
                            turn_id=turn.id,
                            workspace_duckdb_path=str(workspace.duckdb_path),
                            artifacts=resolvable_artifacts,
                            offline_lease_owner_token=maintenance_owner_token or None,
                        )
                        artifact_summary = [
                            {
                                "artifact_id": str(item.get("artifact_id") or ""),
                                "kind": str(item.get("kind") or ""),
                                "path": str(item.get("storage_path") or ""),
                                "payload_format": str(item.get("payload_format") or ""),
                            }
                            for item in persisted_artifacts
                        ]
                    else:
                        artifact_summary = [
                            {
                                **item,
                                "status": "legacy_orphan",
                            }
                            for item in artifact_summary
                        ]

                turn_dir = await TurnBundleService.create_turn_bundle(
                    username=username,
                    workspace_id=conversation.workspace_id,
                    conversation_id=conversation.id,
                    turn_id=turn.id,
                    user_text=turn.user_text,
                    assistant_text=turn.assistant_text,
                    code=str(turn.code_snapshot or ""),
                    manifest=manifest | {"artifacts": artifact_summary},
                )
                turn.storage_path = str(turn_dir)
                turn.code_path = str(TurnBundleService.build_turn_code_path(username, conversation.workspace_id, conversation.id, turn.id))
                turn.manifest_path = str(TurnBundleService.build_turn_manifest_path(username, conversation.workspace_id, conversation.id, turn.id))
                turn.artifact_summary_json = json.dumps(artifact_summary)

                migrated_turn_ids.append(turn.id)
                previous_turn = turn

            if turns and not str(getattr(conversation, "final_turn_id", "") or "").strip():
                latest_turn = turns[-1]
                latest_turn.is_final = True
                conversation.final_turn_id = latest_turn.id
            conversation.migration_version = ConversationMigrationService.CURRENT_MIGRATION_VERSION
            await session.commit()
        finally:
            if maintenance_acquired and maintenance_owner_token:
                await WorkspaceMaintenanceService.release_lease(
                    session,
                    workspace_id=str(conversation.workspace_id),
                    owner_token=maintenance_owner_token,
                )
        return {
            "conversation_id": conversation.id,
            "migration_version": ConversationMigrationService.CURRENT_MIGRATION_VERSION,
            "turn_ids": migrated_turn_ids,
        }
