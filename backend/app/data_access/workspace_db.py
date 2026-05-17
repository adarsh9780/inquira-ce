"""Standardized workspace DuckDB access adapters."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.coordinator import LeaseKinds, ResourceLeaseCoordinator


class WorkspaceRuntimeAdapter:
    """Kernel-owned live workspace DuckDB access."""

    async def get_table_columns(
        self,
        *,
        workspace_id: str,
        table_name: str,
    ) -> list[dict[str, Any]]:
        from app.services.code_executor import get_workspace_table_schema_via_kernel

        schema = await get_workspace_table_schema_via_kernel(
            workspace_id=workspace_id,
            table_name=table_name,
            allow_sample_values=False,
        )
        if not isinstance(schema, list):
            return []
        return [
            {
                "name": str(item.get("name") or ""),
                "dtype": str(item.get("dtype") or ""),
                "description": str(item.get("description") or ""),
                "samples": item.get("samples") if isinstance(item.get("samples"), list) else [],
                "aliases": item.get("aliases") if isinstance(item.get("aliases"), list) else [],
            }
            for item in schema
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]


class WorkspaceOfflineAdapter:
    """Direct workspace DuckDB access for setup and maintenance flows."""

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        owner_token: str | None = None,
        coordinator: ResourceLeaseCoordinator | None = None,
    ) -> None:
        self._session = session
        self._owner_token = str(owner_token or "").strip() or None
        self._coordinator = coordinator or ResourceLeaseCoordinator()

    async def ensure_database_file(self, workspace_duckdb_path: str) -> None:
        await asyncio.to_thread(self._ensure_database_file_sync, workspace_duckdb_path)

    async def drop_table(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        table_name: str,
    ) -> None:
        await self._assert_maintenance_lease(workspace_id)
        if self._session is not None:
            await self._coordinator.assert_no_conflicting_lease(
                self._session,
                resource_key=workspace_id,
                resource_type="workspace",
                conflicting_kinds=(LeaseKinds.WORKSPACE_RUNTIME,),
                owner_token=self._owner_token,
            )
        await asyncio.to_thread(self._drop_table_sync, workspace_duckdb_path, table_name)

    async def read_table_columns(
        self,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
        table_name: str,
    ) -> list[dict[str, Any]]:
        await self._assert_maintenance_lease(workspace_id)
        return await asyncio.to_thread(self._read_table_columns_sync, workspace_duckdb_path, table_name)

    async def _assert_maintenance_lease(self, workspace_id: str) -> None:
        if self._session is None or self._owner_token is None:
            raise RuntimeError("Workspace maintenance lease is required for offline workspace DB access.")
        await self._coordinator.assert_owned_lease(
            self._session,
            resource_key=workspace_id,
            lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
            owner_token=self._owner_token,
        )

    @staticmethod
    def _ensure_database_file_sync(workspace_duckdb_path: str) -> None:
        workspace_db = Path(workspace_duckdb_path)
        if workspace_db.exists():
            return
        parts = {part.lower() for part in workspace_db.expanduser().parts}
        if ".inquira" in parts and "workspaces" in parts:
            raise RuntimeError(
                "Workspace database is missing. "
                f"Expected path: {workspace_db}. "
                "Re-create data by selecting the original dataset again."
            )
        workspace_db.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(workspace_db))
        con.close()

    @staticmethod
    def _drop_table_sync(workspace_duckdb_path: str, table_name: str) -> None:
        db_path = Path(workspace_duckdb_path).expanduser()
        if not db_path.exists():
            return
        escaped_table = str(table_name).replace('"', '""')
        conn = duckdb.connect(str(db_path), read_only=False)
        try:
            conn.execute(f'DROP TABLE IF EXISTS "{escaped_table}"')
        finally:
            conn.close()

    @staticmethod
    def _read_table_columns_sync(workspace_duckdb_path: str, table_name: str) -> list[dict[str, Any]]:
        con = duckdb.connect(workspace_duckdb_path, read_only=True)
        try:
            rows = con.execute(f'DESCRIBE "{table_name}"').fetchall()
            return [
                {
                    "name": str(row[0]),
                    "dtype": str(row[1]),
                    "description": "",
                    "samples": [],
                    "aliases": [],
                }
                for row in rows
            ]
        finally:
            con.close()
