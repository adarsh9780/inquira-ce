"""Approved adapters for scratchpad DuckDB access."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.artifact_scratchpad import ArtifactScratchpadStore
from app.services.code_executor import (
    delete_workspace_artifact_via_kernel,
    get_workspace_artifact_metadata_via_kernel,
    get_workspace_artifact_usage_via_kernel,
    list_workspace_artifacts_via_kernel,
    materialize_workspace_artifacts_via_kernel,
)

from .coordinator import LeaseKinds, ResourceLeaseCoordinator


class ScratchpadRuntimeAdapter:
    """Kernel-owned live access to scratchpad artifact metadata."""

    async def list_workspace_artifacts(
        self,
        *,
        workspace_id: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        return await list_workspace_artifacts_via_kernel(workspace_id, kind=kind)

    async def get_workspace_artifact_metadata(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        return await get_workspace_artifact_metadata_via_kernel(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )

    async def get_workspace_artifact_usage(
        self,
        *,
        workspace_id: str,
    ) -> dict[str, int]:
        return await get_workspace_artifact_usage_via_kernel(workspace_id)

    async def delete_workspace_artifact(
        self,
        *,
        workspace_id: str,
        artifact_id: str,
    ) -> bool:
        return await delete_workspace_artifact_via_kernel(
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )

    async def materialize_workspace_artifacts(
        self,
        *,
        workspace_id: str,
        specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return await materialize_workspace_artifacts_via_kernel(workspace_id, specs)


class ScratchpadOfflineAdapter:
    """Direct scratchpad file access reserved for maintenance-mode flows."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        owner_token: str,
        coordinator: ResourceLeaseCoordinator | None = None,
        store: ArtifactScratchpadStore | None = None,
    ) -> None:
        self._session = session
        self._owner_token = owner_token
        self._coordinator = coordinator or ResourceLeaseCoordinator()
        self._store = store or ArtifactScratchpadStore()

    async def get_workspace_artifact_usage(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
    ) -> dict[str, int]:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.get_workspace_artifact_usage(
            workspace_duckdb_path=workspace_duckdb_path
        )

    async def get_workspace_artifact_metadata(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.get_artifact(
            workspace_duckdb_path=workspace_duckdb_path,
            artifact_id=artifact_id,
        )

    async def list_workspace_artifacts(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.list_artifacts_for_workspace(
            workspace_duckdb_path=workspace_duckdb_path,
            kind=kind,
        )

    async def delete_workspace_artifact(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        artifact_id: str,
    ) -> bool:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.delete_artifact(
            workspace_duckdb_path=workspace_duckdb_path,
            artifact_id=artifact_id,
        )

    async def get_dataframe_rows(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        artifact_id: str,
        offset: int,
        limit: int,
        sort_model: list[dict[str, Any]] | None = None,
        filter_model: dict[str, Any] | None = None,
        search_text: str | None = None,
    ) -> dict[str, Any] | None:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.get_dataframe_rows(
            workspace_duckdb_path=workspace_duckdb_path,
            artifact_id=artifact_id,
            offset=offset,
            limit=limit,
            sort_model=sort_model,
            filter_model=filter_model,
            search_text=search_text,
        )

    async def prune_workspace(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
    ) -> None:
        await self._assert_maintenance_lease(workspace_id)
        self._store.prune_workspace(workspace_duckdb_path=workspace_duckdb_path)

    async def build_scratchpad_db_path(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
    ) -> Path:
        await self._assert_maintenance_lease(workspace_id)
        return self._store.build_scratchpad_db_path(workspace_duckdb_path)

    async def export_dataframe_to_parquet(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        table_name: str,
        storage_path: str,
    ) -> None:
        await self._assert_maintenance_lease(workspace_id)
        self._store.export_dataframe_to_parquet(
            workspace_duckdb_path=workspace_duckdb_path,
            table_name=table_name,
            storage_path=storage_path,
        )

    async def _assert_maintenance_lease(self, workspace_id: str) -> None:
        await self._coordinator.assert_owned_lease(
            self._session,
            resource_key=workspace_id,
            lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
            owner_token=self._owner_token,
        )
