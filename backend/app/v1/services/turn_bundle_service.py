"""Filesystem helpers for turn-scoped analysis bundles."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .workspace_storage_service import WorkspaceStorageService


class TurnBundleService:
    """Create and resolve per-turn bundle folders inside a workspace."""

    ARTIFACT_FORMAT_BY_KIND = {
        "dataframe": "parquet",
        "figure": "json",
        "scalar": "json",
        "structured": "json",
        "text": "txt",
    }

    @staticmethod
    def build_conversations_dir(username: str, workspace_id: str) -> Path:
        return WorkspaceStorageService.build_workspace_dir(username, workspace_id) / "conversations"

    @staticmethod
    def build_conversation_dir(username: str, workspace_id: str, conversation_id: str) -> Path:
        return TurnBundleService.build_conversations_dir(username, workspace_id) / conversation_id

    @staticmethod
    def build_conversation_manifest_path(username: str, workspace_id: str, conversation_id: str) -> Path:
        return TurnBundleService.build_conversation_dir(username, workspace_id, conversation_id) / "conversation.json"

    @staticmethod
    def build_turns_dir(username: str, workspace_id: str, conversation_id: str) -> Path:
        return TurnBundleService.build_conversation_dir(username, workspace_id, conversation_id) / "turns"

    @staticmethod
    def build_turn_dir(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turns_dir(username, workspace_id, conversation_id) / turn_id

    @staticmethod
    def build_turn_user_message_path(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "user.md"

    @staticmethod
    def build_turn_assistant_message_path(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "assistant.md"

    @staticmethod
    def build_turn_code_path(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "analysis.py"

    @staticmethod
    def build_turn_artifacts_dir(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "artifacts"

    @staticmethod
    def build_turn_manifest_path(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "turn.json"

    @staticmethod
    def artifact_payload_format(kind: str | None) -> str:
        normalized = str(kind or "").strip().lower()
        return TurnBundleService.ARTIFACT_FORMAT_BY_KIND.get(normalized, "json")

    @staticmethod
    def build_turn_artifact_path(
        username: str,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        artifact_id: str,
        kind: str | None,
    ) -> Path:
        extension = TurnBundleService.artifact_payload_format(kind)
        return TurnBundleService.build_turn_artifacts_dir(
            username,
            workspace_id,
            conversation_id,
            turn_id,
        ) / f"{artifact_id}.{extension}"

    @staticmethod
    async def create_or_update_conversation_bundle(
        *,
        username: str,
        workspace_id: str,
        conversation_id: str,
        manifest: dict[str, Any] | None = None,
    ) -> Path:
        """Create or refresh conversation.json and return the conversation directory."""
        conversation_dir = TurnBundleService.build_conversation_dir(username, workspace_id, conversation_id)
        manifest_path = TurnBundleService.build_conversation_manifest_path(username, workspace_id, conversation_id)
        existing_payload: dict[str, Any] = {}
        if manifest_path.is_file():
            try:
                raw_existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                raw_existing = {}
            if isinstance(raw_existing, dict):
                existing_payload = raw_existing

        payload = {
            "conversation_id": conversation_id,
            "workspace_id": workspace_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if not existing_payload:
            payload["created_at"] = payload["updated_at"]
        elif existing_payload.get("created_at"):
            payload["created_at"] = existing_payload["created_at"]
        merged_payload = {
            **existing_payload,
            **payload,
        }
        if manifest:
            merged_payload.update(manifest)

        def _write() -> None:
            conversation_dir.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(merged_payload, indent=2), encoding="utf-8")

        await asyncio.to_thread(_write)
        return conversation_dir

    @staticmethod
    async def create_turn_bundle(
        *,
        username: str,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        user_text: str,
        assistant_text: str,
        code: str,
        manifest: dict[str, Any] | None = None,
    ) -> Path:
        """Create the standard turn bundle files and return the turn directory."""
        await TurnBundleService.create_or_update_conversation_bundle(
            username=username,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
        )
        turn_dir = TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id)
        manifest_path = TurnBundleService.build_turn_manifest_path(username, workspace_id, conversation_id, turn_id)
        artifacts_dir = TurnBundleService.build_turn_artifacts_dir(username, workspace_id, conversation_id, turn_id)
        payload = {
            "turn_id": turn_id,
            "conversation_id": conversation_id,
            "workspace_id": workspace_id,
            "created_at": datetime.now(UTC).isoformat(),
            "files": {
                "user_message": "user.md",
                "assistant_message": "assistant.md",
                "analysis_code": "analysis.py",
                "artifacts_dir": "artifacts",
            },
        }
        if manifest:
            payload.update(manifest)

        def _write() -> None:
            turn_dir.mkdir(parents=True, exist_ok=True)
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            TurnBundleService.build_turn_user_message_path(
                username,
                workspace_id,
                conversation_id,
                turn_id,
            ).write_text(user_text, encoding="utf-8")
            TurnBundleService.build_turn_assistant_message_path(
                username,
                workspace_id,
                conversation_id,
                turn_id,
            ).write_text(assistant_text, encoding="utf-8")
            TurnBundleService.build_turn_code_path(
                username,
                workspace_id,
                conversation_id,
                turn_id,
            ).write_text(code, encoding="utf-8")
            manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        await asyncio.to_thread(_write)
        return turn_dir
