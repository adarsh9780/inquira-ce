"""Shared helpers for destructive workspace maintenance operations."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...data_access.coordinator import LeaseConflictError, LeaseKinds, ResourceLeaseCoordinator
from ...services.code_executor import reset_workspace_kernel
from ...services.terminal_executor import stop_workspace_terminal_session


class WorkspaceMaintenanceService:
    """Drain live runtime access, then gate destructive work behind a maintenance lease."""

    _coordinator = ResourceLeaseCoordinator()

    @staticmethod
    async def drain_runtime(
        *,
        workspace_id: str,
        user_id: str | None = None,
    ) -> None:
        """Best-effort stop live runtime handles before maintenance work starts."""
        if user_id:
            try:
                await stop_workspace_terminal_session(user_id=user_id, workspace_id=workspace_id)
            except Exception:
                pass
        try:
            await reset_workspace_kernel(workspace_id)
        except Exception:
            pass

    @classmethod
    async def acquire_lease_or_raise(
        cls,
        session: AsyncSession,
        *,
        workspace_id: str,
        owner_token: str,
        requested_operation: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Acquire the workspace maintenance lease or raise a structured 409."""
        try:
            await cls._coordinator.acquire_workspace_maintenance_lease(
                session,
                workspace_id=workspace_id,
                owner_token=owner_token,
                metadata=metadata,
            )
            await session.commit()
        except LeaseConflictError as exc:
            conflict = await cls._coordinator.get_active_lease(
                session,
                resource_key=workspace_id,
                resource_type="workspace",
                lease_kinds=(LeaseKinds.WORKSPACE_RUNTIME, LeaseKinds.WORKSPACE_MAINTENANCE),
            )
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail=cls.workspace_busy_detail(
                    workspace_id=workspace_id,
                    requested_operation=requested_operation,
                    conflict=conflict,
                ),
            ) from exc

    @classmethod
    async def release_lease(
        cls,
        session: AsyncSession,
        *,
        workspace_id: str,
        owner_token: str,
    ) -> None:
        """Release the workspace maintenance lease if this caller owns it."""
        await cls._coordinator.release_lease(
            session,
            resource_key=workspace_id,
            lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
            owner_token=owner_token,
        )
        await session.commit()

    @staticmethod
    def workspace_busy_detail(
        *,
        workspace_id: str,
        requested_operation: str,
        conflict: Any | None,
    ) -> dict[str, str]:
        """Return the standard machine-readable workspace busy payload."""
        current_operation = "unknown"
        detail = (
            f"Workspace {workspace_id} is busy. Wait for the current workspace operation to finish, "
            f"then retry {requested_operation}."
        )
        if conflict is not None:
            current_operation = str(getattr(conflict, "lease_kind", "") or "unknown")
            metadata_json = str(getattr(conflict, "metadata_json", "") or "").strip()
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
                source = str(metadata.get("source") or "").strip()
                if source:
                    current_operation = source
            detail = (
                f"Workspace {workspace_id} is busy because {current_operation} is still active. "
                f"Wait for it to finish, then retry {requested_operation}."
            )
        return {
            "code": "workspace_busy",
            "detail": detail,
            "resource": workspace_id,
            "current_operation": current_operation,
        }
