"""Migrate workspace files from display-name roots to stable principal roots."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Conversation, Turn, TurnArtifact, Workspace, WorkspaceDataset
from ..db.session import AppDataSessionLocal
from .workspace_storage_service import WorkspaceStorageService


class WorkspaceStorageMigrationService:
    """Move legacy workspace roots and rewrite persisted owned paths."""

    @staticmethod
    def _validate_legacy_root(old_root: Path, *, workspace_id: str) -> None:
        resolved = old_root.expanduser().resolve(strict=False)
        if (
            resolved.name != workspace_id
            or resolved.parent.name != "workspaces"
            or ".inquira" not in resolved.parts
        ):
            raise RuntimeError(
                f"Refusing to migrate workspace {workspace_id}: legacy storage root is not owned by Inquira."
            )

    @staticmethod
    def _rewrite_owned_path(raw_path: str | None, *, old_root: Path, new_root: Path) -> str | None:
        if not raw_path:
            return raw_path
        path = Path(str(raw_path)).expanduser().resolve(strict=False)
        old = old_root.resolve(strict=False)
        if path != old and old not in path.parents:
            return raw_path
        return str(new_root / path.relative_to(old))

    @staticmethod
    async def migrate_workspace(session: AsyncSession, workspace: Workspace) -> bool:
        old_root = Path(str(workspace.duckdb_path)).expanduser().resolve(strict=False).parent
        new_root = WorkspaceStorageService.build_workspace_dir(
            str(workspace.owner_principal_id),
            str(workspace.id),
        ).resolve(strict=False)
        if old_root == new_root:
            return False
        WorkspaceStorageMigrationService._validate_legacy_root(
            old_root,
            workspace_id=str(workspace.id),
        )
        if old_root.exists() and new_root.exists():
            raise RuntimeError(
                f"Cannot migrate workspace {workspace.id}: both legacy and principal storage roots exist."
            )
        if old_root.exists():
            await asyncio.to_thread(new_root.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.move, str(old_root), str(new_root))

        workspace.duckdb_path = WorkspaceStorageMigrationService._rewrite_owned_path(
            workspace.duckdb_path,
            old_root=old_root,
            new_root=new_root,
        ) or str(new_root / "workspace.db")

        datasets = list(
            (await session.execute(select(WorkspaceDataset).where(WorkspaceDataset.workspace_id == workspace.id)))
            .scalars()
            .all()
        )
        conversations = list(
            (await session.execute(select(Conversation).where(Conversation.workspace_id == workspace.id)))
            .scalars()
            .all()
        )
        turns = list(
            (await session.execute(select(Turn).where(Turn.conversation_id.in_([item.id for item in conversations]))))
            .scalars()
            .all()
        ) if conversations else []
        artifacts = list(
            (await session.execute(select(TurnArtifact).where(TurnArtifact.workspace_id == workspace.id)))
            .scalars()
            .all()
        )

        for dataset in datasets:
            dataset.schema_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                dataset.schema_path,
                old_root=old_root,
                new_root=new_root,
            )
        for conversation in conversations:
            conversation.storage_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                conversation.storage_path,
                old_root=old_root,
                new_root=new_root,
            )
        for turn in turns:
            turn.storage_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                turn.storage_path,
                old_root=old_root,
                new_root=new_root,
            )
            turn.code_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                turn.code_path,
                old_root=old_root,
                new_root=new_root,
            )
            turn.manifest_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                turn.manifest_path,
                old_root=old_root,
                new_root=new_root,
            )
        for artifact in artifacts:
            artifact.storage_path = WorkspaceStorageMigrationService._rewrite_owned_path(
                artifact.storage_path,
                old_root=old_root,
                new_root=new_root,
            ) or artifact.storage_path
        return True

    @staticmethod
    async def migrate_all() -> int:
        migrated = 0
        async with AppDataSessionLocal() as session:
            workspaces = list((await session.execute(select(Workspace))).scalars().all())
            for workspace in workspaces:
                if await WorkspaceStorageMigrationService.migrate_workspace(session, workspace):
                    migrated += 1
            await session.commit()
        return migrated
