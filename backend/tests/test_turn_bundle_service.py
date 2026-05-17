from __future__ import annotations

import json

import pytest

from app.v1.services.turn_bundle_service import TurnBundleService


@pytest.mark.asyncio
async def test_create_turn_bundle_writes_expected_files() -> None:
    turn_dir = await TurnBundleService.create_turn_bundle(
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        user_text="Show revenue by month",
        assistant_text="I grouped the data by month.",
        code="print('hello')\n",
        manifest={"status": "draft"},
    )

    assert turn_dir.name == "turn-1"
    assert turn_dir.joinpath("artifacts").is_dir()
    conversation_manifest_path = TurnBundleService.build_conversation_manifest_path(
        "alice",
        "workspace-1",
        "conversation-1",
    )
    assert conversation_manifest_path.is_file()
    assert turn_dir.joinpath("user.md").read_text(encoding="utf-8") == "Show revenue by month"
    assert turn_dir.joinpath("assistant.md").read_text(encoding="utf-8") == "I grouped the data by month."
    assert turn_dir.joinpath("analysis.py").read_text(encoding="utf-8") == "print('hello')\n"

    conversation_manifest = json.loads(conversation_manifest_path.read_text(encoding="utf-8"))
    assert conversation_manifest["conversation_id"] == "conversation-1"
    assert conversation_manifest["workspace_id"] == "workspace-1"

    manifest = json.loads(turn_dir.joinpath("turn.json").read_text(encoding="utf-8"))
    assert manifest["turn_id"] == "turn-1"
    assert manifest["conversation_id"] == "conversation-1"
    assert manifest["workspace_id"] == "workspace-1"
    assert manifest["status"] == "draft"
    assert manifest["files"]["analysis_code"] == "analysis.py"


@pytest.mark.asyncio
async def test_turn_bundle_service_exposes_explicit_paths_and_artifact_formats() -> None:
    artifact_path = TurnBundleService.build_turn_artifact_path(
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        turn_id="turn-1",
        artifact_id="artifact-1",
        kind="dataframe",
    )

    assert TurnBundleService.build_conversation_dir("alice", "workspace-1", "conversation-1").name == "conversation-1"
    assert TurnBundleService.build_turns_dir("alice", "workspace-1", "conversation-1").name == "turns"
    assert TurnBundleService.build_turn_user_message_path("alice", "workspace-1", "conversation-1", "turn-1").name == "user.md"
    assert TurnBundleService.build_turn_assistant_message_path(
        "alice",
        "workspace-1",
        "conversation-1",
        "turn-1",
    ).name == "assistant.md"
    assert TurnBundleService.build_turn_code_path("alice", "workspace-1", "conversation-1", "turn-1").name == "analysis.py"
    assert artifact_path.name == "artifact-1.parquet"
    assert TurnBundleService.artifact_payload_format("figure") == "json"
    assert TurnBundleService.artifact_payload_format("text") == "txt"
    assert TurnBundleService.artifact_payload_format("unknown-kind") == "json"


@pytest.mark.asyncio
async def test_create_or_update_conversation_bundle_preserves_created_at() -> None:
    conversation_dir = await TurnBundleService.create_or_update_conversation_bundle(
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        manifest={"title": "Revenue analysis"},
    )
    first = json.loads(conversation_dir.joinpath("conversation.json").read_text(encoding="utf-8"))

    await TurnBundleService.create_or_update_conversation_bundle(
        username="alice",
        workspace_id="workspace-1",
        conversation_id="conversation-1",
        manifest={"title": "Updated title"},
    )
    second = json.loads(conversation_dir.joinpath("conversation.json").read_text(encoding="utf-8"))

    assert first["created_at"] == second["created_at"]
    assert second["title"] == "Updated title"
