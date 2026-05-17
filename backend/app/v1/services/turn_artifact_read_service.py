"""Read and manage filesystem-backed turn artifacts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.artifact_scratchpad import ArtifactScratchpadStore
from ...services.code_executor import get_workspace_artifact_usage_via_kernel
from ..models import Turn
from ..repositories.turn_artifact_repository import TurnArtifactRepository
from ..repositories.conversation_repository import ConversationRepository
from .turn_bundle_service import TurnBundleService


class TurnArtifactReadService:
    """Serve turn-owned artifact metadata and payloads from filesystem-backed storage."""

    @staticmethod
    async def list_workspace_artifacts(
        session: AsyncSession,
        *,
        workspace_id: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = await TurnArtifactRepository.list_for_workspace(session, workspace_id, kind=kind)
        return [await TurnArtifactReadService._summary_from_row(row) for row in rows]

    @staticmethod
    async def get_workspace_artifact(
        session: AsyncSession,
        *,
        workspace_id: str,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        row = await TurnArtifactRepository.get_for_workspace(
            session,
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )
        if row is None:
            return None
        return await TurnArtifactReadService._metadata_from_row(row)

    @staticmethod
    async def get_dataframe_rows(
        session: AsyncSession,
        *,
        workspace_id: str,
        artifact_id: str,
        offset: int,
        limit: int,
        sort_model: list[dict[str, Any]] | None = None,
        filter_model: dict[str, Any] | None = None,
        search_text: str | None = None,
    ) -> dict[str, Any] | None:
        row = await TurnArtifactRepository.get_for_workspace(
            session,
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )
        if row is None or row.payload_format != "parquet":
            return None
        return await asyncio.to_thread(
            TurnArtifactReadService._read_parquet_rows,
            row,
            offset,
            limit,
            sort_model or [],
            filter_model or {},
            search_text,
        )

    @staticmethod
    async def delete_workspace_artifact(
        session: AsyncSession,
        *,
        workspace_id: str,
        artifact_id: str,
    ) -> bool:
        row = await TurnArtifactRepository.get_for_workspace(
            session,
            workspace_id=workspace_id,
            artifact_id=artifact_id,
        )
        if row is None:
            return False

        storage_path = Path(str(row.storage_path or ""))
        if storage_path.exists():
            await asyncio.to_thread(storage_path.unlink)
        await TurnArtifactRepository.delete_by_id(session, row.id)
        await TurnArtifactReadService._remove_artifact_from_turn_manifest(session, row.turn_id, artifact_id)
        await session.commit()
        return True

    @staticmethod
    async def get_workspace_artifact_usage(
        session: AsyncSession,
        *,
        workspace_id: str,
        workspace_duckdb_path: str,
    ) -> dict[str, int]:
        rows = await TurnArtifactRepository.list_for_workspace(session, workspace_id, statuses=("active",))
        file_bytes = 0
        figure_count = 0
        for row in rows:
            path = Path(str(row.storage_path or ""))
            if path.exists():
                file_bytes += int(path.stat().st_size)
            if str(row.kind or "").strip().lower() == "figure":
                figure_count += 1

        try:
            legacy_usage = await get_workspace_artifact_usage_via_kernel(workspace_id)
        except RuntimeError:
            legacy_usage = ArtifactScratchpadStore().get_workspace_artifact_usage(
                workspace_duckdb_path=workspace_duckdb_path
            )
        return {
            "duckdb_bytes": file_bytes + int(legacy_usage.get("duckdb_bytes") or 0),
            "figure_count": figure_count + int(legacy_usage.get("figure_count") or 0),
        }

    @staticmethod
    async def _summary_from_row(row) -> dict[str, Any]:
        path = Path(str(row.storage_path or ""))
        row_count = None
        schema = None
        if row.payload_format == "parquet" and path.exists():
            row_count, schema = await asyncio.to_thread(TurnArtifactReadService._read_parquet_stats, path)
        return {
            "artifact_id": row.artifact_id,
            "logical_name": row.logical_name or row.artifact_id,
            "kind": row.kind,
            "row_count": row_count,
            "schema": schema,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "status": row.status,
        }

    @staticmethod
    async def _metadata_from_row(row) -> dict[str, Any]:
        path = Path(str(row.storage_path or ""))
        row_count = None
        schema = None
        payload = None
        table_name = None

        if row.payload_format == "parquet" and path.exists():
            row_count, schema = await asyncio.to_thread(TurnArtifactReadService._read_parquet_stats, path)
        elif path.exists():
            payload = await asyncio.to_thread(TurnArtifactReadService._read_payload_file, path)

        return {
            "artifact_id": row.artifact_id,
            "run_id": row.turn_id,
            "workspace_id": row.workspace_id,
            "logical_name": row.logical_name or row.artifact_id,
            "kind": row.kind,
            "pointer": str(path),
            "table_name": table_name,
            "schema": schema,
            "row_count": row_count,
            "payload": payload,
            "created_at": row.created_at.isoformat() if row.created_at else "",
            "expires_at": "",
            "status": row.status,
            "error": None,
        }

    @staticmethod
    def _read_payload_file(path: Path) -> dict[str, Any] | None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return raw if isinstance(raw, dict) else {"value": raw}

    @staticmethod
    def _read_parquet_stats(path: Path) -> tuple[int, list[dict[str, Any]]]:
        con = duckdb.connect()
        try:
            schema_rows = con.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",
                [str(path)],
            ).fetchall()
            row_count = con.execute(
                "SELECT COUNT(*) FROM read_parquet(?)",
                [str(path)],
            ).fetchone()
        finally:
            con.close()
        schema = [{"name": str(item[0]), "dtype": str(item[1] or "")} for item in schema_rows]
        return int((row_count or [0])[0] or 0), schema

    @staticmethod
    def _read_parquet_rows(
        row,
        offset: int,
        limit: int,
        sort_model: list[dict[str, Any]],
        filter_model: dict[str, Any],
        search_text: str | None,
    ) -> dict[str, Any]:
        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(1000, int(limit)))
        storage_path = Path(str(row.storage_path or ""))
        con = duckdb.connect()
        try:
            sample_df = con.execute(
                "SELECT * FROM read_parquet(?) LIMIT 0",
                [str(storage_path)],
            ).fetchdf()
            all_columns = [str(col) for col in list(sample_df.columns)]
            where_sql, where_params = ArtifactScratchpadStore.build_dataframe_where_clause(
                column_names=all_columns,
                filter_model=filter_model,
                search_text=search_text,
            )
            order_sql = ArtifactScratchpadStore.build_dataframe_order_clause(
                column_names=all_columns,
                sort_model=sort_model,
            )
            page_df = con.execute(
                f"SELECT * FROM read_parquet(?) {where_sql} {order_sql} LIMIT {safe_limit} OFFSET {safe_offset}",
                [str(storage_path), *where_params],
            ).fetchdf()
            row_count = con.execute(
                f"SELECT COUNT(*) FROM read_parquet(?) {where_sql}",
                [str(storage_path), *where_params],
            ).fetchone()
        finally:
            con.close()
        rows = json.loads(page_df.to_json(orient="records", date_format="iso"))
        return {
            "artifact_id": row.artifact_id,
            "name": row.logical_name or row.artifact_id,
            "row_count": int((row_count or [0])[0] or 0),
            "columns": all_columns,
            "rows": rows,
            "offset": safe_offset,
            "limit": safe_limit,
        }

    @staticmethod
    async def _remove_artifact_from_turn_manifest(
        session: AsyncSession,
        turn_id: str,
        artifact_id: str,
    ) -> None:
        turn = await ConversationRepository.get_turn(session, turn_id)
        if turn is None:
            return
        artifacts = []
        if turn.artifact_summary_json:
            try:
                raw_artifacts = json.loads(turn.artifact_summary_json)
            except json.JSONDecodeError:
                raw_artifacts = []
            if isinstance(raw_artifacts, list):
                artifacts = [
                    item for item in raw_artifacts
                    if isinstance(item, dict) and str(item.get("artifact_id") or "") != artifact_id
                ]
        turn.artifact_summary_json = json.dumps(artifacts)

        manifest_path = Path(str(turn.manifest_path or ""))
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest = {}
            raw_manifest_artifacts = manifest.get("artifacts")
            if isinstance(raw_manifest_artifacts, list):
                manifest["artifacts"] = [
                    item for item in raw_manifest_artifacts
                    if isinstance(item, dict) and str(item.get("artifact_id") or "") != artifact_id
                ]
                await asyncio.to_thread(
                    manifest_path.write_text,
                    json.dumps(manifest, indent=2),
                    encoding="utf-8",
                )
