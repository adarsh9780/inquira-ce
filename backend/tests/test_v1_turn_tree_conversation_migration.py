from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.v1.services.conversation_migration_service import ConversationMigrationService


@pytest.mark.asyncio
async def test_migrate_conversation_backfills_linear_lineage_and_turn_bundles(monkeypatch) -> None:
    conversation = SimpleNamespace(id="conv-1", workspace_id="ws-1", migration_version=None)
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
        code_path=None,
        manifest_path=None,
        artifact_summary_json=None,
        execution_summary_json=json.dumps({"success": True}),
    )
    turns = [turn_one, turn_two]

    async def fake_get_conversation(_session, _conversation_id):
        return conversation

    async def fake_ensure_workspace_access(_session, _principal_id, _workspace_id):
        return SimpleNamespace(id="ws-1")

    async def fake_list_turns_in_sequence(_session, _conversation_id):
        return turns

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

    result = await ConversationMigrationService.migrate_conversation(
        session=session,
        principal_id="principal-1",
        conversation_id="conv-1",
        username="alice",
    )

    assert result["turn_ids"] == ["turn-1", "turn-2"]
    assert conversation.migration_version == 1
    assert turn_two.parent_turn_id == "turn-1"

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
