"""Workspace dataset ingestion service.

This service imports source files into workspace DuckDB and stores metadata
records in the v1 workspace dataset catalog.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path

import duckdb
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WorkspaceDataset
from ..repositories.workspace_repository import WorkspaceRepository


class DatasetService:
    """Ingest and manage workspace datasets."""

    @staticmethod
    def _normalize_table_name(source_path: str) -> str:
        stem = Path(source_path).stem
        clean = "".join(c if c.isalnum() else "_" for c in stem).lower() or "dataset"
        suffix = hashlib.md5(source_path.encode("utf-8")).hexdigest()[:8]
        return f"{clean}__{suffix}"

    @staticmethod
    def _source_fingerprint(source_path: str) -> str:
        return hashlib.md5(source_path.strip().encode("utf-8")).hexdigest()

    @staticmethod
    async def list_datasets(session: AsyncSession, user_id: str, workspace_id: str) -> list[WorkspaceDataset]:
        """List datasets in a workspace owned by user."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        result = await session.execute(
            select(WorkspaceDataset)
            .where(WorkspaceDataset.workspace_id == workspace_id)
            .order_by(WorkspaceDataset.updated_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_dataset(session: AsyncSession, user, workspace_id: str, source_path: str) -> WorkspaceDataset:
        """Ingest dataset into workspace DuckDB and persist metadata."""
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, user.id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")

        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise HTTPException(status_code=404, detail="Source file not found")

        table_name = DatasetService._normalize_table_name(str(source))
        fingerprint = DatasetService._source_fingerprint(str(source))
        file_type = source.suffix.lower().lstrip(".")

        def _ingest() -> tuple[int, str]:
            con = duckdb.connect(workspace.duckdb_path)
            try:
                if file_type in {"csv", "tsv"}:
                    con.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)",
                        [str(source)],
                    )
                elif file_type == "parquet":
                    con.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet(?)",
                        [str(source)],
                    )
                elif file_type == "json":
                    con.execute(
                        f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_json_auto(?)",
                        [str(source)],
                    )
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

                row_count = int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
                schema_rows = con.execute(f"DESCRIBE {table_name}").fetchall()
                schema = {
                    "table_name": table_name,
                    "columns": [
                        {
                            "name": r[0],
                            "dtype": r[1],
                            "description": "",
                            "samples": [],
                        }
                        for r in schema_rows
                    ],
                }
            finally:
                con.close()

            schema_dir = Path(workspace.duckdb_path).parent / "meta"
            schema_dir.mkdir(parents=True, exist_ok=True)
            schema_path = schema_dir / f"{table_name}_schema.json"
            with schema_path.open("w", encoding="utf-8") as file:
                json.dump(schema, file, indent=2)
            return row_count, str(schema_path)

        row_count, schema_path = await asyncio.to_thread(_ingest)

        existing_result = await session.execute(
            select(WorkspaceDataset).where(
                WorkspaceDataset.workspace_id == workspace_id,
                WorkspaceDataset.source_fingerprint == fingerprint,
            )
        )
        existing = existing_result.scalar_one_or_none()

        source_mtime = os.path.getmtime(source)
        if existing:
            existing.source_path = str(source)
            existing.table_name = table_name
            existing.schema_path = schema_path
            existing.file_size = source.stat().st_size
            existing.source_mtime = source_mtime
            existing.row_count = row_count
            existing.file_type = file_type
            dataset = existing
        else:
            dataset = WorkspaceDataset(
                workspace_id=workspace_id,
                source_path=str(source),
                source_fingerprint=fingerprint,
                table_name=table_name,
                schema_path=schema_path,
                file_size=source.stat().st_size,
                source_mtime=source_mtime,
                row_count=row_count,
                file_type=file_type,
            )
            session.add(dataset)

        await session.commit()
        await session.refresh(dataset)
        return dataset
