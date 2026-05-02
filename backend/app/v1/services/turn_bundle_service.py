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

    @staticmethod
    def build_conversations_dir(username: str, workspace_id: str) -> Path:
        return WorkspaceStorageService.build_workspace_dir(username, workspace_id) / "conversations"

    @staticmethod
    def build_conversation_dir(username: str, workspace_id: str, conversation_id: str) -> Path:
        return TurnBundleService.build_conversations_dir(username, workspace_id) / conversation_id

    @staticmethod
    def build_turns_dir(username: str, workspace_id: str, conversation_id: str) -> Path:
        return TurnBundleService.build_conversation_dir(username, workspace_id, conversation_id) / "turns"

    @staticmethod
    def build_turn_dir(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turns_dir(username, workspace_id, conversation_id) / turn_id

    @staticmethod
    def build_turn_manifest_path(username: str, workspace_id: str, conversation_id: str, turn_id: str) -> Path:
        return TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id) / "turn.json"

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
        turn_dir = TurnBundleService.build_turn_dir(username, workspace_id, conversation_id, turn_id)
        manifest_path = turn_dir / "turn.json"
        artifacts_dir = turn_dir / "artifacts"
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
            (turn_dir / "user.md").write_text(user_text, encoding="utf-8")
            (turn_dir / "assistant.md").write_text(assistant_text, encoding="utf-8")
            (turn_dir / "analysis.py").write_text(code, encoding="utf-8")
            manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        await asyncio.to_thread(_write)
        return turn_dir
