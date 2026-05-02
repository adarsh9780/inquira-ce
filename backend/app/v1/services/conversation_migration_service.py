"""Helpers to backfill legacy conversations into the turn-tree bundle model."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Turn
from ..repositories.conversation_repository import ConversationRepository
from .conversation_service import ConversationService
from .turn_bundle_service import TurnBundleService


class ConversationMigrationService:
    """Backfill older linear conversations into the new turn-based structure."""

    CURRENT_MIGRATION_VERSION = 1

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
        await ConversationService.ensure_workspace_access(session, principal_id, conversation.workspace_id)

        turns = await ConversationRepository.list_turns_in_sequence(session, conversation_id)
        previous_turn: Turn | None = None
        migrated_turn_ids: list[str] = []

        for turn in turns:
            if previous_turn is not None and not str(turn.parent_turn_id or "").strip():
                turn.parent_turn_id = previous_turn.id

            artifact_summary = ConversationMigrationService._artifact_summary(turn)
            manifest = {
                "seq_no": turn.seq_no,
                "parent_turn_id": turn.parent_turn_id,
                "result_kind": str(turn.result_kind or ""),
                "artifacts": artifact_summary,
            }
            if turn.execution_summary_json:
                manifest["execution"] = ConversationMigrationService._safe_json(turn.execution_summary_json)

            needs_bundle = not str(turn.manifest_path or "").strip() or not str(turn.code_path or "").strip()
            if needs_bundle:
                turn_dir = await TurnBundleService.create_turn_bundle(
                    username=username,
                    workspace_id=conversation.workspace_id,
                    conversation_id=conversation.id,
                    turn_id=turn.id,
                    user_text=turn.user_text,
                    assistant_text=turn.assistant_text,
                    code=str(turn.code_snapshot or ""),
                    manifest=manifest,
                )
                turn.code_path = str(turn_dir / "analysis.py")
                turn.manifest_path = str(turn_dir / "turn.json")

            if not str(turn.artifact_summary_json or "").strip():
                turn.artifact_summary_json = json.dumps(artifact_summary)

            migrated_turn_ids.append(turn.id)
            previous_turn = turn

        if turns and not str(getattr(conversation, "final_turn_id", "") or "").strip():
            latest_turn = turns[-1]
            latest_turn.is_final = True
            conversation.final_turn_id = latest_turn.id
        conversation.migration_version = ConversationMigrationService.CURRENT_MIGRATION_VERSION
        await session.commit()
        return {
            "conversation_id": conversation.id,
            "migration_version": ConversationMigrationService.CURRENT_MIGRATION_VERSION,
            "turn_ids": migrated_turn_ids,
        }
