"""Persist turn-owned artifact payloads into workspace folders."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.turn_artifact_repository import TurnArtifactRepository
from .storage_path_policy import resolve_owned_path
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
        await asyncio.to_thread(artifacts_dir.mkdir, parents=True, exist_ok=True)

        persisted_rows: list[dict[str, Any]] = []
        for item in normalized_artifacts:
            persisted = await TurnArtifactStorageService._persist_one_artifact(
                username=username,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                workspace_duckdb_path=workspace_duckdb_path,
                artifact=item,
                session=session,
                offline_lease_owner_token=offline_lease_owner_token,
            )
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
        artifact: dict[str, Any],
        session: AsyncSession,
        offline_lease_owner_token: str | None,
    ) -> dict[str, Any]:
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        source_artifact_id = str(artifact.get("source_artifact_id") or artifact_id).strip()
        kind = str(artifact.get("kind") or "").strip().lower() or "scalar"
        logical_name = str(artifact.get("logical_name") or artifact_id or kind).strip() or kind
        display_name = str(artifact.get("display_name") or "").strip() or TurnArtifactStorageService.display_name_for_artifact(logical_name)
        payload_format = TurnBundleService.artifact_payload_format(kind)
        raw_storage_path = str(artifact.get("storage_path") or "").strip()
        storage_path = Path(raw_storage_path).expanduser() if raw_storage_path else None
        if storage_path is None:
            raise FileNotFoundError(
                f"Turn artifact {artifact_id or logical_name!r} does not include a storage_path."
            )

        owned_artifacts_dir = TurnBundleService.build_turn_artifacts_dir(
            username,
            workspace_id,
            conversation_id,
            turn_id,
        )
        storage_path = resolve_owned_path(
            storage_path,
            root=owned_artifacts_dir,
            label="Turn artifact path",
        )

        source_meta: dict[str, Any] = artifact
        if not storage_path.exists():
            raise FileNotFoundError(
                f"Turn artifact file is missing for {artifact_id or logical_name!r}: {storage_path}"
            )
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
