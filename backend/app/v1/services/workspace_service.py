"""Workspace business logic service."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, Workspace
from ..repositories.workspace_repository import WorkspaceRepository
from .workspace_storage_service import WorkspaceStorageService


class WorkspaceService:
    """Create/manage workspaces with plan limits and filesystem provisioning."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize workspace names for case-insensitive uniqueness."""
        return " ".join(name.strip().split()).lower()

    @staticmethod
    async def list_user_workspaces(session: AsyncSession, user_id: str) -> list[Workspace]:
        """Return user workspaces sorted by recency."""
        return await WorkspaceRepository.list_for_user(session, user_id)

    @staticmethod
    async def create_workspace(session: AsyncSession, user: User, name: str) -> Workspace:
        """Create workspace while enforcing unique-name and plan limits."""
        normalized = WorkspaceService.normalize_name(name)
        if not normalized:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty")

        existing = await WorkspaceRepository.get_by_name_normalized(session, user.id, normalized)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Workspace name already exists")

        count = await WorkspaceRepository.count_for_user(session, user.id)
        if user.plan.value == "FREE" and count >= 1:
            raise HTTPException(
                status_code=403,
                detail="You are on the Free plan and can create only 1 workspace. Upgrade your plan to create more.",
            )

        is_active = 1 if count == 0 else 0
        placeholder_id = "temp"
        duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.username, placeholder_id))

        workspace = await WorkspaceRepository.create(
            session=session,
            user_id=user.id,
            name=name.strip(),
            name_normalized=normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
        )

        await WorkspaceStorageService.ensure_workspace_dirs(user.username, workspace.id)
        workspace.duckdb_path = str(WorkspaceStorageService.build_duckdb_path(user.username, workspace.id))
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def activate_workspace(session: AsyncSession, user_id: str, workspace_id: str) -> Workspace:
        """Set one workspace active for the user."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        await WorkspaceRepository.deactivate_all_for_user(session, user_id)
        workspace.is_active = 1
        await session.commit()
        await session.refresh(workspace)
        return workspace

    @staticmethod
    async def delete_workspace(session: AsyncSession, user: User, workspace_id: str) -> None:
        """Hard delete workspace DB row and filesystem directory."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        await WorkspaceRepository.delete(session, workspace)
        await session.commit()
        await WorkspaceStorageService.hard_delete_workspace(user.username, workspace_id)

        remaining = await WorkspaceRepository.list_for_user(session, user.id)
        if remaining and not any(ws.is_active == 1 for ws in remaining):
            remaining[0].is_active = 1
            await session.commit()
