from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.conversation_migration_service import ConversationMigrationService


@pytest.mark.asyncio
async def test_migrate_conversation_backfills_linear_lineage_and_turn_bundles(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", title="Legacy revenue analysis", migration_version=None, storage_path=None)
    turn_one = SimpleNamespace(
        id="turn-1",
        conversation_id="conv-1",
        parent_turn_id=None,
        seq_no=1,
        result_kind=None,
        user_text="Load orders",
        assistant_text="Loaded orders.",
        metadata_json=None,
        code_snapshot="print('one')\n",
        storage_path=None,
        code_path=None,
        manifest_path=None,
        artifact_summary_json=None,
        execution_summary_json=None,
    )
    turn_two = SimpleNamespace(
        id="turn-2",
        conversation_id="conv-1",
        parent_turn_id=None,
        seq_no=2,
        result_kind="dataframe",
        user_text="Aggregate revenue",
        assistant_text="Aggregated revenue.",
        metadata_json=json.dumps({"artifacts": [{"artifact_id": "df-1", "kind": "dataframe", "path": "artifacts/df-1.parquet"}]}),
        code_snapshot="print('two')\n",
        storage_path=None,
        code_path=None,
        manifest_path=None,
        artifact_summary_json=None,
        execution_summary_json=json.dumps({"success": True}),
    )
    turns = [turn_one, turn_two]

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1", duckdb_path="/tmp/workspace.db")

    async def fake_list_turns_in_sequence(_session, _conversation_id):
        return turns

    async def fake_list_turn_artifacts(_session, _turn_id, *, include_deleted=False):
        _ = include_deleted
        return []

    async def fake_persist_turn_artifacts(*, session, username, workspace_id, conversation_id, turn_id, workspace_duckdb_path, artifacts):
        _ = session, username, workspace_id, conversation_id, turn_id, workspace_duckdb_path, artifacts
        turn_dir = (
            Path.home()
            / ".inquira"
            / "alice"
            / "workspaces"
            / "ws-1"
            / "conversations"
            / "conv-1"
            / "turns"
            / "turn-2"
        )
        artifacts_dir = turn_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        stored_path = artifacts_dir / "df-1.parquet"
        stored_path.write_bytes(b"PAR1")
        return [
            {
                "artifact_id": "df-1",
                "kind": "dataframe",
                "storage_path": str(stored_path),
                "payload_format": "parquet",
            }
        ]

    session = SimpleNamespace()

    async def _commit():
        return None

    session.commit = _commit

    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.ConversationRepository.get_conversation",
        fake_get_conversation,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.ConversationService.ensure_workspace_access",
        fake_ensure_workspace_access,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.ConversationRepository.list_turns_in_sequence",
        fake_list_turns_in_sequence,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.TurnArtifactRepository.list_for_turn",
        fake_list_turn_artifacts,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.TurnArtifactStorageService.persist_turn_artifacts",
        fake_persist_turn_artifacts,
    )

    result = await ConversationMigrationService.migrate_conversation(
        session=session,
        principal_id="principal-1",
        conversation_id="conv-1",
        username="alice",
    )

    assert result["turn_ids"] == ["turn-1", "turn-2"]
    assert conversation.migration_version == 2
    assert turn_two.parent_turn_id == "turn-1"
    assert conversation.storage_path is not None
    assert turn_two.storage_path is not None

    conversation_manifest = (
        Path.home()
        / ".inquira"
        / "alice"
        / "workspaces"
        / "ws-1"
        / "conversations"
        / "conv-1"
        / "conversation.json"
    )
    assert json.loads(conversation_manifest.read_text(encoding="utf-8"))["title"] == "Legacy revenue analysis"
    turn_two_dir = (
        Path.home()
        / ".inquira"
        / "alice"
        / "workspaces"
        / "ws-1"
        / "conversations"
        / "conv-1"
        / "turns"
        / "turn-2"
    )
    assert turn_two_dir.joinpath("analysis.py").read_text(encoding="utf-8") == "print('two')\n"
    manifest = json.loads(turn_two_dir.joinpath("turn.json").read_text(encoding="utf-8"))
    assert manifest["parent_turn_id"] == "turn-1"
    assert manifest["artifacts"][0]["artifact_id"] == "df-1"
    assert manifest["artifacts"][0]["path"] == str(turn_two_dir / "artifacts" / "df-1.parquet")


@pytest.mark.asyncio
async def test_migrate_pending_conversations_once_only_processes_outdated_rows(monkeypatch) -> None:
    pending = [
        SimpleNamespace(id="conv-1", created_by_principal_id="principal-1"),
        SimpleNamespace(id="conv-2", created_by_principal_id="principal-2"),
    ]
    migrated: list[tuple[str, str, str]] = []

    async def fake_list_pending(_session, *, target_version, limit):
        assert target_version == 2
        assert limit == 100
        return pending

    async def fake_get_principal(_session, principal_id):
        return SimpleNamespace(id=principal_id, username_cached=f"user-{principal_id}")

    async def fake_migrate_conversation(*, session, principal_id, conversation_id, username):
        _ = session
        migrated.append((principal_id, conversation_id, username))
        return {"conversation_id": conversation_id}

    class _SessionContext:
        async def __aenter__(self):
            return SimpleNamespace()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.AppDataSessionLocal",
        lambda: _SessionContext(),
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.ConversationRepository.list_conversations_needing_migration",
        fake_list_pending,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.PrincipalRepository.get_by_id",
        fake_get_principal,
    )
    monkeypatch.setattr(
        "app.v1.services.conversation_migration_service.ConversationMigrationService.migrate_conversation",
        fake_migrate_conversation,
    )

    await ConversationMigrationService.migrate_pending_conversations_once()

    assert migrated == [
        ("principal-1", "conv-1", "user-principal-1"),
        ("principal-2", "conv-2", "user-principal-2"),
    ]
