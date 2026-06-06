from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.v1.db.base import AppDataBase
from app.v1.models import Conversation, Principal, Turn, TurnArtifact, Workspace
from app.v1.services.workspace_storage_migration_service import WorkspaceStorageMigrationService
from app.v1.services.workspace_storage_service import WorkspaceStorageService


def test_storage_owner_key_never_allows_path_components() -> None:
    key = WorkspaceStorageService.storage_owner_key("../../other-user")

    assert "/" not in key
    assert "\\" not in key
    assert key not in {".", ".."}


@pytest.mark.asyncio
async def test_workspace_storage_migration_moves_files_and_rewrites_owned_paths(monkeypatch, tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'appdata.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(AppDataBase.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    legacy_root = tmp_path / ".inquira" / "legacy-name" / "workspaces" / "workspace-1"
    legacy_turn = legacy_root / "conversations" / "conversation-1" / "turn-1"
    legacy_turn.mkdir(parents=True)
    artifact_path = legacy_turn / "result.json"
    artifact_path.write_text('{"value": 1}', encoding="utf-8")
    (legacy_root / "workspace.db").touch()

    principal_root = tmp_path / "principal-roots"
    monkeypatch.setattr(
        WorkspaceStorageService,
        "_user_root",
        staticmethod(lambda principal_id: principal_root / principal_id / "workspaces"),
    )

    async with sessions() as session:
        session.add(Principal(id="principal-1", username_cached="Legacy Name", plan_cached="FREE"))
        workspace = Workspace(
            id="workspace-1",
            owner_principal_id="principal-1",
            name="Workspace",
            name_normalized="workspace",
            duckdb_path=str(legacy_root / "workspace.db"),
            is_active=1,
        )
        conversation = Conversation(
            id="conversation-1",
            workspace_id="workspace-1",
            created_by_principal_id="principal-1",
            title="Conversation",
            storage_path=str(legacy_turn.parent),
        )
        turn = Turn(
            id="turn-1",
            conversation_id="conversation-1",
            seq_no=1,
            user_text="Question",
            assistant_text="Answer",
            storage_path=str(legacy_turn),
            code_path=str(legacy_turn / "analysis.py"),
            manifest_path=str(legacy_turn / "turn.json"),
        )
        artifact = TurnArtifact(
            workspace_id="workspace-1",
            conversation_id="conversation-1",
            turn_id="turn-1",
            artifact_id="artifact-1",
            kind="scalar",
            storage_path=str(artifact_path),
            payload_format="json",
        )
        session.add_all([workspace, conversation, turn, artifact])
        await session.commit()

        migrated = await WorkspaceStorageMigrationService.migrate_workspace(session, workspace)
        await session.commit()

        expected_root = principal_root / "principal-1" / "workspaces" / "workspace-1"
        assert migrated is True
        assert legacy_root.exists() is False
        assert (expected_root / "conversations" / "conversation-1" / "turn-1" / "result.json").is_file()
        assert Path(workspace.duckdb_path).parent == expected_root
        assert Path(conversation.storage_path).is_relative_to(expected_root)
        assert Path(turn.storage_path).is_relative_to(expected_root)
        assert Path(artifact.storage_path).is_relative_to(expected_root)

    await engine.dispose()


@pytest.mark.asyncio
async def test_workspace_storage_migration_rejects_external_legacy_root(tmp_path) -> None:
    external_root = tmp_path / "external" / "workspace-1"
    external_root.mkdir(parents=True)
    workspace = Workspace(
        id="workspace-1",
        owner_principal_id="principal-1",
        name="Workspace",
        name_normalized="workspace",
        duckdb_path=str(external_root / "workspace.db"),
        is_active=1,
    )

    with pytest.raises(RuntimeError, match="not owned by Inquira"):
        await WorkspaceStorageMigrationService.migrate_workspace(None, workspace)  # type: ignore[arg-type]

    assert external_root.is_dir()
