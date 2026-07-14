"""Resolve global AI defaults and workspace-scoped overrides."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key
from ...services.llm_runtime_config import load_llm_runtime_config
from ..repositories.preferences_repository import PreferencesRepository
from ..repositories.workspace_repository import WorkspaceRepository
from .secret_storage_service import SecretStorageService


class WorkspaceAIConfigService:
    """Single source of truth for effective workspace AI configuration."""

    OVERRIDE_FIELDS = (
        "llm_provider_override",
        "main_model_override",
        "lite_model_override",
        "llm_temperature_override",
        "llm_max_tokens_override",
        "llm_top_p_override",
    )

    @staticmethod
    def _clean_optional(value: Any) -> str | None:
        cleaned = str(value or "").strip()
        return cleaned or None

    @classmethod
    async def resolve(
        cls,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        workspace: Any | None = None,
    ) -> dict[str, Any]:
        workspace = workspace or await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        prefs = await PreferencesRepository.get_or_create(session, principal_id)
        runtime = load_llm_runtime_config()

        default_provider = normalize_llm_provider(getattr(prefs, "llm_provider", runtime.provider))
        provider_override = cls._clean_optional(getattr(workspace, "llm_provider_override", None))
        effective_provider = normalize_llm_provider(provider_override or default_provider)

        defaults = {
            "provider": default_provider,
            "main_model": str(getattr(prefs, "selected_model", runtime.default_model) or runtime.default_model).strip(),
            "lite_model": str(getattr(prefs, "selected_lite_model", runtime.lite_model) or runtime.lite_model).strip(),
            "temperature": float(getattr(prefs, "llm_temperature", 0.7)),
            "max_tokens": int(getattr(prefs, "llm_max_tokens", runtime.default_max_tokens)),
            "top_p": float(getattr(prefs, "llm_top_p", 1.0)),
        }
        overrides = {
            "provider": provider_override,
            "main_model": cls._clean_optional(getattr(workspace, "main_model_override", None)),
            "lite_model": cls._clean_optional(getattr(workspace, "lite_model_override", None)),
            "temperature": getattr(workspace, "llm_temperature_override", None),
            "max_tokens": getattr(workspace, "llm_max_tokens_override", None),
            "top_p": getattr(workspace, "llm_top_p_override", None),
            "allow_llm_data_samples": bool(getattr(workspace, "allow_llm_data_samples", False)),
        }
        effective = {
            "provider": effective_provider,
            "main_model": overrides["main_model"] or defaults["main_model"],
            "lite_model": overrides["lite_model"] or defaults["lite_model"],
            "temperature": defaults["temperature"] if overrides["temperature"] is None else float(overrides["temperature"]),
            "max_tokens": defaults["max_tokens"] if overrides["max_tokens"] is None else int(overrides["max_tokens"]),
            "top_p": defaults["top_p"] if overrides["top_p"] is None else float(overrides["top_p"]),
            "allow_llm_data_samples": overrides["allow_llm_data_samples"],
        }
        requires_key = provider_requires_api_key(effective_provider)
        try:
            key_present = bool(SecretStorageService.get_api_key(principal_id, provider=effective_provider))
        except RuntimeError:
            key_present = False
        credential_ready = not requires_key or key_present
        model_ready = bool(effective["main_model"] and effective["lite_model"])

        sources = {
            key: ("workspace" if overrides.get(key) is not None else "application")
            for key in ("provider", "main_model", "lite_model", "temperature", "max_tokens", "top_p")
        }
        sources["allow_llm_data_samples"] = "workspace"
        effective["sources"] = sources
        readiness = {
            "credential_ready": credential_ready,
            "model_ready": model_ready,
            "configuration_reviewed": bool(getattr(workspace, "ai_config_reviewed", False)),
            "ready": credential_ready and model_ready and bool(getattr(workspace, "ai_config_reviewed", False)),
            "credential_source": "application",
            "requires_api_key": requires_key,
        }
        return {
            "workspace": workspace,
            "defaults": defaults,
            "overrides": overrides,
            "effective": effective,
            "readiness": readiness,
        }

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
        payload: Any,
    ) -> dict[str, Any]:
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace.llm_provider_override = cls._clean_optional(payload.llm_provider_override)
        workspace.main_model_override = cls._clean_optional(payload.main_model_override)
        workspace.lite_model_override = cls._clean_optional(payload.lite_model_override)
        workspace.llm_temperature_override = payload.llm_temperature_override
        workspace.llm_max_tokens_override = payload.llm_max_tokens_override
        workspace.llm_top_p_override = payload.llm_top_p_override
        workspace.allow_llm_data_samples = bool(payload.allow_llm_data_samples)
        workspace.ai_config_reviewed = True
        await session.commit()
        return await cls.resolve(session, principal_id, workspace_id)

    @classmethod
    async def reset_overrides(
        cls,
        session: AsyncSession,
        principal_id: str,
        workspace_id: str,
    ) -> dict[str, Any]:
        workspace = await WorkspaceRepository.get_by_id(session, workspace_id, principal_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        for field in cls.OVERRIDE_FIELDS:
            setattr(workspace, field, None)
        await session.commit()
        return await cls.resolve(session, principal_id, workspace_id)

    @staticmethod
    def public_response(workspace_id: str, resolved: dict[str, Any]) -> dict[str, Any]:
        return {
            "workspace_id": workspace_id,
            "defaults": resolved["defaults"],
            "overrides": resolved["overrides"],
            "effective": resolved["effective"],
            "readiness": resolved["readiness"],
        }
