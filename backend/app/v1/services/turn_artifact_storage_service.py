"""Persist turn-owned artifact payloads into workspace folders."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import duckdb
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.artifact_scratchpad import ArtifactScratchpadStore
from ..repositories.turn_artifact_repository import TurnArtifactRepository
from .turn_bundle_service import TurnBundleService


class TurnArtifactStorageService:
    """Write artifact payloads to turn folders and mirror lightweight metadata to SQLite."""

    @staticmethod
    async def persist_turn_artifacts(
        *,
        session: AsyncSession,
        username: str,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        workspace_duckdb_path: str,
        artifacts: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        normalized_artifacts = [item for item in (artifacts or []) if isinstance(item, dict)]
        artifacts_dir = TurnBundleService.build_turn_artifacts_dir(
            username,
            workspace_id,
            conversation_id,
            turn_id,
        )
        scratchpad = ArtifactScratchpadStore()
        scratchpad_db_path = scratchpad.build_scratchpad_db_path(workspace_duckdb_path)

        def _reset_artifacts_dir() -> None:
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            artifacts_dir.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(_reset_artifacts_dir)

        persisted_rows: list[dict[str, Any]] = []
        for item in normalized_artifacts:
            persisted_rows.append(
                await TurnArtifactStorageService._persist_one_artifact(
                    username=username,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    scratchpad_db_path=scratchpad_db_path,
                    artifact=item,
                    scratchpad=scratchpad,
                )
            )

        await TurnArtifactRepository.replace_for_turn(
            session,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            items=persisted_rows,
        )
        return persisted_rows

    @staticmethod
    async def _persist_one_artifact(
        *,
        username: str,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        workspace_duckdb_path: str,
        scratchpad_db_path: Path,
        artifact: dict[str, Any],
        scratchpad: ArtifactScratchpadStore,
    ) -> dict[str, Any]:
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        kind = str(artifact.get("kind") or "").strip().lower() or "scalar"
        logical_name = str(artifact.get("logical_name") or artifact_id or kind).strip() or kind
        payload_format = TurnBundleService.artifact_payload_format(kind)
        storage_path = TurnBundleService.build_turn_artifact_path(
            username,
            workspace_id,
            conversation_id,
            turn_id,
            artifact_id or logical_name,
            kind,
        )

        scratchpad_meta = scratchpad.get_artifact(
            workspace_duckdb_path=workspace_duckdb_path,
            artifact_id=artifact_id,
        ) if artifact_id else None
        source_meta = scratchpad_meta if isinstance(scratchpad_meta, dict) else artifact

        await asyncio.to_thread(
            TurnArtifactStorageService._write_artifact_payload,
            scratchpad_db_path,
            storage_path,
            kind,
            source_meta,
        )

        return {
            "artifact_id": artifact_id or logical_name,
            "kind": kind,
            "logical_name": logical_name,
            "storage_path": str(storage_path),
            "payload_format": payload_format,
            "size_bytes": int(storage_path.stat().st_size) if storage_path.exists() else None,
            "status": "active",
            "row_count": source_meta.get("row_count"),
            "schema": source_meta.get("schema"),
            "table_name": source_meta.get("table_name"),
            "created_at": str(source_meta.get("created_at") or ""),
            "payload": source_meta.get("payload"),
        }

    @staticmethod
    def _write_artifact_payload(
        scratchpad_db_path: Path,
        storage_path: Path,
        kind: str,
        source_meta: dict[str, Any],
    ) -> None:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "dataframe":
            TurnArtifactStorageService._write_dataframe_payload(
                scratchpad_db_path=scratchpad_db_path,
                storage_path=storage_path,
                table_name=str(source_meta.get("table_name") or "").strip(),
            )
            return

        payload = source_meta.get("payload")
        if kind == "text":
            if isinstance(payload, dict):
                text_value = payload.get("value")
            else:
                text_value = payload
            storage_path.write_text(str(text_value or ""), encoding="utf-8")
            return

        serializable_payload = payload
        if serializable_payload is None:
            serializable_payload = source_meta
        storage_path.write_text(
            json.dumps(serializable_payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _write_dataframe_payload(
        *,
        scratchpad_db_path: Path,
        storage_path: Path,
        table_name: str,
    ) -> None:
        if not table_name:
            storage_path.write_text("[]", encoding="utf-8")
            return
        escaped_table = table_name.replace('"', '""')
        escaped_path = str(storage_path).replace("'", "''")
        con = duckdb.connect(str(scratchpad_db_path), read_only=True)
        try:
            con.execute(
                f"COPY (SELECT * FROM \"{escaped_table}\") TO '{escaped_path}' (FORMAT PARQUET)"
            )
        finally:
            con.close()
