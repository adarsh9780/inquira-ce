"""Workspace business logic service."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.code_executor import reset_workspace_kernel
from ...services.terminal_executor import stop_workspace_terminal_session
from ..models import Workspace
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .workspace_storage_service import WorkspaceStorageService


class WorkspaceService:
    """Create/manage workspaces and filesystem provisioning."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize workspace names for case-insensitive uniqueness."""
        return " ".join(name.strip().split()).lower()

    @staticmethod
    async def list_user_workspaces(session: AsyncSession, principal_id: str) -> list[Workspace]:
        """Return user workspaces sorted by recency."""
        workspaces = await WorkspaceRepository.list_for_principal(session, principal_id)
        active_jobs = await WorkspaceDeletionRepository.list_active_for_principal(session, principal_id)
        deleting_workspace_ids = {job.workspace_id for job in active_jobs}
        return [ws for ws in workspaces if ws.id not in deleting_workspace_ids]

    @staticmethod
    async def create_workspace(session: AsyncSession, user, name: str) -> Workspace:
        """Create workspace while enforcing unique-name rules."""
        normalized = WorkspaceService.normalize_name(name)
        if not normalized:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

        existing = await WorkspaceRepository.get_by_name_normalized(session, user.id, normalized)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Workspace name already exists")

        count = await WorkspaceRepository.count_for_principal(session, user.id)
        is_active = 1 if count == 0 else 0
        placeholder_id = "temp"
        duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.username, placeholder_id))

        workspace = await WorkspaceRepository.create(
            session=session,
            principal_id=user.id,
            name=name.strip(),
            name_normalized=normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
        )

        await WorkspaceStorageService.ensure_workspace_dirs(user.username, workspace.id)
        workspace.duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.username, workspace.id))
        await session.commit()
        await session.refresh(workspace)
        await WorkspaceStorageService.write_workspace_manifest(
            username=user.username,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            normalized_name=workspace.name_normalized,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        return workspace

    @staticmethod
    async def activate_workspace(session: AsyncSession, user, workspace_id: str) -> Workspace:
        """Set one workspace active for the user."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        await WorkspaceRepository.deactivate_all_for_principal(session, user.id)
        workspace.is_active = 1
        await session.commit()
        await session.refresh(workspace)
        await WorkspaceStorageService.write_workspace_manifest(
            username=user.username,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            normalized_name=workspace.name_normalized,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        return workspace

    @staticmethod
    async def rename_workspace(session: AsyncSession, user, workspace_id: str, name: str) -> Workspace:
        """Rename workspace while preserving normalized uniqueness rules."""
        normalized = WorkspaceService.normalize_name(name)
        if not normalized:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if workspace.name_normalized != normalized:
            existing = await WorkspaceRepository.get_by_name_normalized(session, user.id, normalized)
            if existing is not None and existing.id != workspace.id:
                raise HTTPException(status_code=409, detail="Workspace name already exists")

        workspace.name = name.strip()
        workspace.name_normalized = normalized
        await session.commit()
        await session.refresh(workspace)
        await WorkspaceStorageService.write_workspace_manifest(
            username=user.username,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            normalized_name=workspace.name_normalized,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        return workspace

    @staticmethod
    async def clear_workspace_database(session: AsyncSession, user, workspace_id: str) -> tuple[bool, str]:
        """Clear workspace DB and local dataset metadata so the user can re-import data."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Release runtime/kernel file handles before touching workspace DB files.
        try:
            await stop_workspace_terminal_session(user_id=str(user.id), workspace_id=workspace_id)
        except Exception:
            pass
        try:
            await reset_workspace_kernel(workspace_id)
        except Exception:
            pass

        datasets = await DatasetRepository.list_for_workspace(session, workspace_id)
        schema_paths = [
            Path(str(ds.schema_path)).expanduser()
            for ds in datasets
            if isinstance(ds.schema_path, str) and ds.schema_path.strip()
        ]

        workspace_db = Path(str(workspace.duckdb_path)).expanduser()
        workspace_dir = workspace_db.parent
        candidates = {
            workspace_db,
            workspace_dir / "workspace.db",
            workspace_dir / "workspace.duckdb",
        }
        scratchpad_dir = workspace_dir / "scratchpad"

        def _clear_files() -> bool:
            removed_any = False

            for path in candidates:
                try:
                    if path.exists() and path.is_file():
                        path.unlink()
                        removed_any = True
                except OSError as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Could not clear workspace database because it is locked or unavailable. "
                            f"Path: {path} ({exc})"
                        ),
                    ) from exc

            for schema_path in schema_paths:
                try:
                    if schema_path.exists() and schema_path.is_file():
                        schema_path.unlink()
                        removed_any = True
                except OSError:
                    continue

            if scratchpad_dir.exists():
                try:
                    shutil.rmtree(scratchpad_dir)
                    removed_any = True
                except OSError as exc:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Could not clear workspace scratchpad because files are locked. "
                            f"Path: {scratchpad_dir} ({exc})"
                        ),
                    ) from exc

            return removed_any

        cleared = await asyncio.to_thread(_clear_files)
        await DatasetRepository.delete_for_workspace(session, workspace_id)
        await session.commit()
        detail = (
            "Workspace database cleared. Re-create data by selecting the original dataset."
            if cleared
            else "Workspace database was already empty. Re-create data by selecting the original dataset."
        )
        return cleared, detail

    @staticmethod
    async def delete_workspace(session: AsyncSession, user, workspace_id: str) -> None:
        """Hard delete workspace DB row and filesystem directory."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        await WorkspaceRepository.delete(session, workspace)
        await session.commit()
        await WorkspaceStorageService.hard_delete_workspace(user.username, workspace_id)

        remaining = await WorkspaceRepository.list_for_principal(session, user.id)
        if remaining and not any(ws.is_active == 1 for ws in remaining):
            remaining[0].is_active = 1
            await session.commit()
