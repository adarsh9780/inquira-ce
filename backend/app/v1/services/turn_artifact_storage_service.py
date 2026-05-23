"""Persist turn-owned artifact payloads into workspace folders."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...data_access import ScratchpadOfflineAdapter, ScratchpadRuntimeAdapter
from ...core.logger import logprint
from ...services.artifact_scratchpad import ArtifactScratchpadStore
from ..repositories.turn_artifact_repository import TurnArtifactRepository
from .turn_bundle_service import TurnBundleService


class TurnArtifactStorageService:
    """Write artifact payloads to turn folders and mirror lightweight metadata to SQLite."""

    @staticmethod
    def slugify_artifact_name(value: str | None, *, fallback: str = "artifact") -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
        normalized = re.sub(r"_+", "_", normalized).strip("._-")
        return normalized[:96] or fallback

    @staticmethod
    def display_name_for_artifact(value: str | None, *, fallback: str = "Artifact") -> str:
        normalized = str(value or "").strip().replace("_", " ").replace("-", " ")
        normalized = " ".join(normalized.split())
        return normalized.title() if normalized else fallback

    @staticmethod
    def _artifact_id_with_name(
        *,
        source_artifact_id: str,
        logical_name: str,
        kind: str,
        used_ids: set[str],
    ) -> str:
        fallback = TurnArtifactStorageService.slugify_artifact_name(kind or "artifact")
        name_slug = TurnArtifactStorageService.slugify_artifact_name(logical_name, fallback=fallback)
        source_slug = TurnArtifactStorageService.slugify_artifact_name(source_artifact_id, fallback="")
        if source_slug and name_slug.lower() in source_slug.lower():
            candidate = source_slug
        elif source_slug:
            candidate = f"{name_slug}__{source_slug}"
        else:
            candidate = name_slug

        base = candidate
        suffix = 2
        while candidate in used_ids:
            candidate = f"{base}__{suffix}"
            suffix += 1
        used_ids.add(candidate)
        return candidate

    @staticmethod
    def _normalize_artifact_identities(
        artifacts: list[dict[str, Any]],
        *,
        turn_id: str,
    ) -> list[dict[str, Any]]:
        used_ids: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(artifacts, start=1):
            kind = str(item.get("kind") or "").strip().lower() or "scalar"
            source_artifact_id = str(item.get("artifact_id") or "").strip()
            logical_name = str(
                item.get("logical_name")
                or item.get("display_name")
                or item.get("name")
                or item.get("result_name")
                or source_artifact_id
                or f"{kind}_{index}"
            ).strip()
            artifact_id = TurnArtifactStorageService._artifact_id_with_name(
                source_artifact_id=source_artifact_id,
                logical_name=logical_name,
                kind=kind,
                used_ids=used_ids,
            )
            normalized.append(
                {
                    **item,
                    "artifact_id": artifact_id,
                    "source_artifact_id": source_artifact_id or artifact_id,
                    "kind": kind,
                    "logical_name": logical_name,
                    "display_name": str(item.get("display_name") or "").strip()
                    or TurnArtifactStorageService.display_name_for_artifact(logical_name),
                    "turn_id": turn_id,
                }
            )
        return normalized

    @staticmethod
    def response_artifact_from_row(item: dict[str, Any]) -> dict[str, Any]:
        logical_name = str(item.get("logical_name") or item.get("artifact_id") or "artifact")
        display_name = str(item.get("display_name") or "").strip() or TurnArtifactStorageService.display_name_for_artifact(logical_name)
        summary = {
            "artifact_id": str(item.get("artifact_id") or ""),
            "source_artifact_id": str(item.get("source_artifact_id") or item.get("artifact_id") or ""),
            "kind": str(item.get("kind") or ""),
            "logical_name": logical_name,
            "display_name": display_name,
            "storage_path": str(item.get("storage_path") or ""),
            "payload_format": str(item.get("payload_format") or ""),
            "row_count": item.get("row_count"),
            "schema": item.get("schema"),
            "preview_rows": item.get("preview_rows"),
            "table_name": item.get("table_name"),
            "created_at": str(item.get("created_at") or ""),
        }
        if item.get("payload") is not None:
            summary["payload"] = item.get("payload")
        return summary

    @staticmethod
    def response_artifacts_from_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [TurnArtifactStorageService.response_artifact_from_row(item) for item in items]

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
        offline_lease_owner_token: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_artifacts = TurnArtifactStorageService._normalize_artifact_identities(
            [item for item in (artifacts or []) if isinstance(item, dict)],
            turn_id=turn_id,
        )
        artifacts_dir = TurnBundleService.build_turn_artifacts_dir(
            username,
            workspace_id,
            conversation_id,
            turn_id,
        )
        scratchpad_db_path = ArtifactScratchpadStore.build_scratchpad_db_path(workspace_duckdb_path)

        def _reset_artifacts_dir() -> None:
            if artifacts_dir.exists():
                shutil.rmtree(artifacts_dir)
            artifacts_dir.mkdir(parents=True, exist_ok=True)

        await asyncio.to_thread(_reset_artifacts_dir)

        materialized_sizes: dict[str, int | None] = {}
        kernel_specs = [
            {
                "artifact_id": str(item.get("source_artifact_id") or item.get("artifact_id") or "").strip(),
                "kind": str(item.get("kind") or "").strip().lower() or "scalar",
                "payload": item.get("payload"),
                "table_name": item.get("table_name"),
                "storage_path": str(
                    TurnBundleService.build_turn_artifact_path(
                        username,
                        workspace_id,
                        conversation_id,
                        turn_id,
                        str(item.get("artifact_id") or item.get("logical_name") or item.get("kind") or "artifact"),
                        str(item.get("kind") or ""),
                    )
                ),
            }
            for item in normalized_artifacts
            if str(item.get("source_artifact_id") or item.get("artifact_id") or "").strip()
        ]
        if kernel_specs:
            try:
                materialized = await ScratchpadRuntimeAdapter().materialize_workspace_artifacts(
                    workspace_id=workspace_id,
                    specs=kernel_specs,
                )
            except Exception as exc:  # noqa: BLE001
                logprint(
                    "Workspace kernel artifact materialization failed; continuing without local shadow copies.",
                    level="WARNING",
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    error=str(exc),
                )
                materialized = []
            materialized_sizes = {
                str(item.get("artifact_id") or ""): item.get("size_bytes")
                for item in materialized
                if isinstance(item, dict)
            }

        persisted_rows: list[dict[str, Any]] = []
        for item in normalized_artifacts:
            try:
                persisted = await TurnArtifactStorageService._persist_one_artifact(
                    username=username,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    scratchpad_db_path=scratchpad_db_path,
                    artifact=item,
                    kernel_materialized_sizes=materialized_sizes,
                    session=session,
                    offline_lease_owner_token=offline_lease_owner_token,
                )
            except Exception as exc:  # noqa: BLE001
                logprint(
                    "Skipping turn artifact shadow persistence after artifact write failure.",
                    level="WARNING",
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    artifact_id=str(item.get("artifact_id") or ""),
                    kind=str(item.get("kind") or ""),
                    error=str(exc),
                )
                continue
            if persisted is not None:
                persisted_rows.append(persisted)

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
        kernel_materialized_sizes: dict[str, int | None],
        session: AsyncSession,
        offline_lease_owner_token: str | None,
    ) -> dict[str, Any] | None:
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        source_artifact_id = str(artifact.get("source_artifact_id") or artifact_id).strip()
        kind = str(artifact.get("kind") or "").strip().lower() or "scalar"
        logical_name = str(artifact.get("logical_name") or artifact_id or kind).strip() or kind
        display_name = str(artifact.get("display_name") or "").strip() or TurnArtifactStorageService.display_name_for_artifact(logical_name)
        payload_format = TurnBundleService.artifact_payload_format(kind)
        storage_path = TurnBundleService.build_turn_artifact_path(
            username,
            workspace_id,
            conversation_id,
            turn_id,
            artifact_id or logical_name,
            kind,
        )

        source_meta: dict[str, Any] = artifact
        needs_scratchpad_lookup = False
        if kind == "dataframe":
            needs_scratchpad_lookup = not str(artifact.get("table_name") or "").strip()
        elif kind in {"figure", "scalar", "text", "structured"}:
            needs_scratchpad_lookup = artifact.get("payload") is None
        scratchpad_fallback_allowed = False
        if needs_scratchpad_lookup and source_artifact_id:
            try:
                kernel_meta = await ScratchpadRuntimeAdapter().get_workspace_artifact_metadata(
                    workspace_id=workspace_id,
                    artifact_id=source_artifact_id,
                )
            except RuntimeError:
                kernel_meta = None
                scratchpad_fallback_allowed = bool(offline_lease_owner_token)
            if isinstance(kernel_meta, dict):
                source_meta = kernel_meta
            elif scratchpad_fallback_allowed:
                scratchpad_meta = await ScratchpadOfflineAdapter(
                    session=session,
                    owner_token=str(offline_lease_owner_token),
                ).get_workspace_artifact_metadata(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    artifact_id=source_artifact_id,
                )
                if isinstance(scratchpad_meta, dict):
                    source_meta = scratchpad_meta
        size_bytes = kernel_materialized_sizes.get(source_artifact_id)
        if size_bytes is None and not storage_path.exists():
            if kind == "dataframe" and not scratchpad_fallback_allowed:
                TurnArtifactStorageService._log_artifact_shadow_skip(
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    artifact_id=artifact_id,
                    kind=kind,
                    reason="Dataframe artifact export was not materialized by the workspace kernel.",
                )
                return None
            if kind == "dataframe":
                await ScratchpadOfflineAdapter(
                    session=session,
                    owner_token=str(offline_lease_owner_token),
                ).export_dataframe_to_parquet(
                    workspace_id=workspace_id,
                    workspace_duckdb_path=workspace_duckdb_path,
                    table_name=str(source_meta.get("table_name") or "").strip(),
                    storage_path=str(storage_path),
                )
            if kind in {"figure", "scalar", "text", "structured"} and not scratchpad_fallback_allowed:
                serializable_payload = source_meta.get("payload")
                if serializable_payload is None:
                    TurnArtifactStorageService._log_artifact_shadow_skip(
                        workspace_id=workspace_id,
                        conversation_id=conversation_id,
                        turn_id=turn_id,
                        artifact_id=artifact_id,
                        kind=kind,
                        reason="Artifact payload metadata is unavailable because the workspace kernel is not active.",
                    )
                    return None
            if kind != "dataframe":
                await asyncio.to_thread(
                    TurnArtifactStorageService._write_artifact_payload,
                    scratchpad_db_path,
                    storage_path,
                    kind,
                    source_meta,
                )
            size_bytes = int(storage_path.stat().st_size) if storage_path.exists() else None

        if not storage_path.exists():
            TurnArtifactStorageService._log_artifact_shadow_skip(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                artifact_id=artifact_id,
                kind=kind,
                reason="Local artifact shadow file is missing after materialization.",
            )
            return None
        if size_bytes is None:
            size_bytes = int(storage_path.stat().st_size)

        return {
            "artifact_id": artifact_id or logical_name,
            "source_artifact_id": source_artifact_id or artifact_id or logical_name,
            "kind": kind,
            "logical_name": logical_name,
            "display_name": display_name,
            "storage_path": str(storage_path),
            "payload_format": payload_format,
            "size_bytes": size_bytes,
            "status": "active",
            "row_count": source_meta.get("row_count"),
            "schema": source_meta.get("schema"),
            "preview_rows": source_meta.get("preview_rows"),
            "table_name": source_meta.get("table_name"),
            "created_at": str(source_meta.get("created_at") or ""),
            "payload": source_meta.get("payload"),
        }

    @staticmethod
    def _log_artifact_shadow_skip(
        *,
        workspace_id: str,
        conversation_id: str,
        turn_id: str,
        artifact_id: str,
        kind: str,
        reason: str,
    ) -> None:
        logprint(
            "Skipping turn artifact local shadow copy.",
            level="WARNING",
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            artifact_id=artifact_id,
            kind=kind,
            reason=reason,
        )

    @staticmethod
    def _write_artifact_payload(
        scratchpad_db_path: Path,
        storage_path: Path,
        kind: str,
        source_meta: dict[str, Any],
    ) -> None:
        storage_path.parent.mkdir(parents=True, exist_ok=True)
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
