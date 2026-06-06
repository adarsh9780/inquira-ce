"""Workspace business logic service."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.logger import logprint
from ...data_access.coordinator import LeaseConflictError, ResourceLeaseCoordinator
from ...services.code_executor import reset_workspace_kernel
from ...services.terminal_executor import stop_workspace_terminal_session
from ..models import Workspace
from ..repositories.conversation_repository import ConversationRepository
from ..repositories.dataset_repository import DatasetRepository
from ..repositories.principal_repository import PrincipalRepository
from ..repositories.workspace_deletion_repository import WorkspaceDeletionRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .workspace_maintenance_service import WorkspaceMaintenanceService
from .workspace_storage_service import WorkspaceStorageService


class WorkspaceService:
    """Create/manage workspaces and filesystem provisioning."""

    _activation_leases = ResourceLeaseCoordinator()

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
    async def get_workspace_summary(session: AsyncSession, user, workspace_id: str) -> dict:
        """Return lightweight workspace metadata for on-demand UI details."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        datasets = await DatasetRepository.list_for_workspace(session, workspace_id)
        conversation_count = await ConversationRepository.count_for_workspace(session, workspace_id)

        return {
            "id": workspace.id,
            "name": workspace.name,
            "is_active": bool(workspace.is_active),
            "schema_context": str(getattr(workspace, "schema_context", "") or ""),
            "created_at": workspace.created_at,
            "updated_at": workspace.updated_at,
            "table_count": len(datasets),
            "table_names": [str(dataset.table_name) for dataset in datasets if str(dataset.table_name or "").strip()],
            "conversation_count": int(conversation_count),
        }

    @staticmethod
    async def create_workspace(session: AsyncSession, user, name: str, schema_context: str = "") -> Workspace:
        """Create workspace while enforcing unique-name rules."""
        normalized = WorkspaceService.normalize_name(name)
        if not normalized:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

        existing = await WorkspaceRepository.get_by_name_normalized(session, user.id, normalized)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Workspace name already exists")

        principal = await PrincipalRepository.get_by_id(session, user.id)
        if principal is None:
            raise HTTPException(status_code=404, detail="Principal not found")

        count = await WorkspaceRepository.count_for_principal(session, user.id)
        is_active = 1 if count == 0 and not principal.active_workspace_id else 0
        placeholder_id = "temp"
        duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.id, placeholder_id))

        workspace = await WorkspaceRepository.create(
            session=session,
            principal_id=user.id,
            name=name.strip(),
            name_normalized=normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
            schema_context=str(schema_context or ""),
        )

        await WorkspaceStorageService.ensure_workspace_dirs(user.id, workspace.id)
        workspace.duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.id, workspace.id))
        if count == 0 or not principal.active_workspace_id:
            await WorkspaceService._set_active_workspace_atomic(
                session=session,
                principal_id=str(user.id),
                workspace_id=str(workspace.id),
            )
        await session.commit()
        await session.refresh(workspace)
        await WorkspaceStorageService.write_workspace_manifest(
            username=user.id,
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

        previous_active = await WorkspaceRepository.get_active_for_principal(session, user.id)
        await WorkspaceService._set_active_workspace_atomic(
            session=session,
            principal_id=str(user.id),
            workspace_id=str(workspace.id),
        )
        await session.commit()
        await session.refresh(workspace)

        previous_workspace_id = str(getattr(previous_active, "id", "") or "").strip()
        if previous_workspace_id and previous_workspace_id != str(workspace.id):
            try:
                await stop_workspace_terminal_session(
                    user_id=str(user.id),
                    workspace_id=previous_workspace_id,
                )
            except Exception as exc:
                logprint(
                    "Failed to stop previous workspace terminal session during activation switch.",
                    level="WARNING",
                    user_id=str(user.id),
                    previous_workspace_id=previous_workspace_id,
                    error=str(exc),
                )
            try:
                await reset_workspace_kernel(previous_workspace_id)
            except Exception as exc:
                logprint(
                    "Failed to reset previous workspace kernel during activation switch.",
                    level="WARNING",
                    user_id=str(user.id),
                    previous_workspace_id=previous_workspace_id,
                    error=str(exc),
                )

        await WorkspaceStorageService.write_workspace_manifest(
            username=user.id,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            normalized_name=workspace.name_normalized,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
        )
        return workspace

    @staticmethod
    async def update_workspace(
        session: AsyncSession,
        user,
        workspace_id: str,
        name: str | None = None,
        schema_context: str | None = None,
    ) -> Workspace:
        """Update workspace metadata while preserving normalized uniqueness rules."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        if name is not None:
            normalized = WorkspaceService.normalize_name(name)
            if not normalized:
                raise HTTPException(status_code=400, detail="Workspace name cannot be empty")
            if workspace.name_normalized != normalized:
                existing = await WorkspaceRepository.get_by_name_normalized(session, user.id, normalized)
                if existing is not None and existing.id != workspace.id:
                    raise HTTPException(status_code=409, detail="Workspace name already exists")
            workspace.name = name.strip()
            workspace.name_normalized = normalized
        if schema_context is not None:
            workspace.schema_context = str(schema_context or "")
        await session.commit()
        await session.refresh(workspace)
        await WorkspaceStorageService.write_workspace_manifest(
            username=user.id,
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
        return await WorkspaceService.update_workspace(session, user, workspace_id, name=name)

    @staticmethod
    async def clear_workspace_database(session: AsyncSession, user, workspace_id: str) -> tuple[bool, str]:
        """Clear workspace DB and local dataset metadata so the user can re-import data."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        maintenance_owner_token = f"workspace-clear:{workspace_id}:{uuid.uuid4()}"
        await WorkspaceMaintenanceService.drain_runtime(
            workspace_id=workspace_id,
            user_id=str(user.id),
        )
        await WorkspaceMaintenanceService.acquire_lease_or_raise(
            session,
            workspace_id=workspace_id,
            owner_token=maintenance_owner_token,
            requested_operation="clear_workspace_database",
            metadata={"source": "workspace_database_clear"},
        )

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

            return removed_any

        try:
            cleared = await asyncio.to_thread(_clear_files)
            await DatasetRepository.delete_for_workspace(session, workspace_id)
            await session.commit()
            detail = (
                "Workspace database cleared. Re-create data by selecting the original dataset."
                if cleared
                else "Workspace database was already empty. Re-create data by selecting the original dataset."
            )
            return cleared, detail
        finally:
            await WorkspaceMaintenanceService.release_lease(
                session,
                workspace_id=workspace_id,
                owner_token=maintenance_owner_token,
            )

    @staticmethod
    async def delete_workspace(session: AsyncSession, user, workspace_id: str) -> None:
        """Hard delete workspace DB row and filesystem directory."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        maintenance_owner_token = f"workspace-delete:{workspace_id}:{uuid.uuid4()}"
        await WorkspaceMaintenanceService.drain_runtime(
            workspace_id=workspace_id,
            user_id=str(user.id),
        )
        await WorkspaceMaintenanceService.acquire_lease_or_raise(
            session,
            workspace_id=workspace_id,
            owner_token=maintenance_owner_token,
            requested_operation="delete_workspace",
            metadata={"source": "workspace_delete"},
        )

        try:
            was_active = bool(getattr(workspace, "is_active", 0))
            await WorkspaceRepository.delete(session, workspace)
            remaining = await WorkspaceRepository.list_for_principal(session, user.id)
            next_workspace_id = str(remaining[0].id) if was_active and remaining else None
            if was_active or next_workspace_id is None:
                await WorkspaceService._set_active_workspace_atomic(
                    session=session,
                    principal_id=str(user.id),
                    workspace_id=next_workspace_id,
                )
            await session.commit()
            await WorkspaceStorageService.hard_delete_workspace(user.id, workspace_id)
        finally:
            await WorkspaceMaintenanceService.release_lease(
                session,
                workspace_id=workspace_id,
                owner_token=maintenance_owner_token,
            )

    @staticmethod
    async def _set_active_workspace_atomic(
        *,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str | None,
    ) -> None:
        owner_token = f"workspace-activation:{principal_id}:{uuid.uuid4()}"
        try:
            await WorkspaceService._activation_leases.acquire_principal_activation_lease(
                session,
                principal_id=principal_id,
                owner_token=owner_token,
                metadata={"workspace_id": workspace_id or ""},
            )
            await PrincipalRepository.set_active_workspace_id(
                session,
                principal_id=principal_id,
                workspace_id=workspace_id,
            )
            await WorkspaceRepository.set_active_for_principal(
                session,
                principal_id=principal_id,
                workspace_id=workspace_id,
            )
            await WorkspaceService._activation_leases.release_lease(
                session,
                resource_key=principal_id,
                lease_kind="principal_activation",
                owner_token=owner_token,
            )
        except LeaseConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail="Another workspace activation is already in progress.",
            ) from exc
        except Exception:
            await WorkspaceService._activation_leases.release_lease(
                session,
                resource_key=principal_id,
                lease_kind="principal_activation",
                owner_token=owner_token,
            )
            raise
