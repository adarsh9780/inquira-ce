from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1.schemas.workspace import WorkspaceAIConfigUpdateRequest
from app.v1.services.workspace_ai_config_service import WorkspaceAIConfigService
from app.v1.services.chat_service import ChatService


class _Session:
    committed = False

    async def commit(self):
        self.committed = True


def _workspace(**overrides):
    values = {
        "id": "workspace-1",
        "llm_provider_override": None,
        "main_model_override": None,
        "lite_model_override": None,
        "llm_temperature_override": None,
        "llm_max_tokens_override": None,
        "llm_top_p_override": None,
        "allow_llm_data_samples": False,
        "ai_config_reviewed": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _preferences():
    return SimpleNamespace(
        llm_provider="openrouter",
        selected_model="global-main",
        selected_lite_model="global-lite",
        llm_temperature=0.7,
        llm_max_tokens=4096,
        llm_top_p=1.0,
    )


@pytest.mark.asyncio
async def test_workspace_ai_config_resolves_partial_overrides_and_explicit_privacy(monkeypatch):
    workspace = _workspace(
        main_model_override="workspace-main",
        llm_temperature_override=0.25,
        allow_llm_data_samples=True,
    )

    async def _workspace_by_id(_session, workspace_id, principal_id):
        assert (workspace_id, principal_id) == ("workspace-1", "user-1")
        return workspace

    async def _preferences_for_user(_session, _principal_id):
        return _preferences()

    monkeypatch.setattr("app.v1.services.workspace_ai_config_service.WorkspaceRepository.get_by_id", _workspace_by_id)
    monkeypatch.setattr("app.v1.services.workspace_ai_config_service.PreferencesRepository.get_or_create", _preferences_for_user)
    monkeypatch.setattr("app.v1.services.workspace_ai_config_service.SecretStorageService.get_api_key", lambda *_args, **_kwargs: "secret")

    resolved = await WorkspaceAIConfigService.resolve(_Session(), "user-1", "workspace-1")

    assert resolved["effective"]["main_model"] == "workspace-main"
    assert resolved["effective"]["lite_model"] == "global-lite"
    assert resolved["effective"]["temperature"] == 0.25
    assert resolved["effective"]["allow_llm_data_samples"] is True
    assert resolved["effective"]["sources"]["main_model"] == "workspace"
    assert resolved["effective"]["sources"]["lite_model"] == "application"
    assert resolved["readiness"]["ready"] is True
    assert resolved["readiness"]["credential_source"] == "application"


@pytest.mark.asyncio
async def test_workspace_ai_config_update_and_reset_never_store_credentials(monkeypatch):
    workspace = _workspace()

    async def _workspace_by_id(_session, _workspace_id, _principal_id):
        return workspace

    async def _resolve(_session, _principal_id, _workspace_id):
        return {"workspace": workspace, "defaults": {}, "overrides": {}, "effective": {}, "readiness": {}}

    monkeypatch.setattr("app.v1.services.workspace_ai_config_service.WorkspaceRepository.get_by_id", _workspace_by_id)
    monkeypatch.setattr(WorkspaceAIConfigService, "resolve", _resolve)
    session = _Session()
    payload = WorkspaceAIConfigUpdateRequest(
        llm_provider_override="openai",
        main_model_override="gpt-main",
        lite_model_override="gpt-lite",
        allow_llm_data_samples=True,
    )

    await WorkspaceAIConfigService.update(session, "user-1", "workspace-1", payload)
    assert workspace.llm_provider_override == "openai"
    assert workspace.main_model_override == "gpt-main"
    assert workspace.allow_llm_data_samples is True
    assert workspace.ai_config_reviewed is True
    assert not hasattr(workspace, "api_key")

    await WorkspaceAIConfigService.reset_overrides(session, "user-1", "workspace-1")
    assert workspace.llm_provider_override is None
    assert workspace.main_model_override is None
    assert workspace.allow_llm_data_samples is True


@pytest.mark.asyncio
async def test_chat_runtime_uses_workspace_models_provider_and_privacy(monkeypatch):
    workspace = _workspace(
        llm_provider_override="openai",
        main_model_override="workspace-main",
        lite_model_override="workspace-lite",
        llm_temperature_override=0.2,
        allow_llm_data_samples=True,
    )

    async def _global_preferences(_session, _principal_id):
        return {
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "requires_api_key": True,
            "selected_main_model": "global-main",
            "selected_lite_model": "global-lite",
            "selected_coding_model": "global-main",
            "temperature": 0.7,
            "max_tokens": 4096,
            "top_p": 1.0,
            "top_k": 0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "allow_llm_data_samples": False,
            "context_windows": {},
        }

    async def _workspace_by_id(_session, _workspace_id, _principal_id):
        return workspace

    monkeypatch.setattr(ChatService, "_resolve_llm_preferences", staticmethod(_global_preferences))
    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", _workspace_by_id)
    session = SimpleNamespace(execute=lambda *_args: None)

    resolved = await ChatService._resolve_workspace_llm_preferences(session, "user-1", "workspace-1")

    assert resolved["provider"] == "openai"
    assert resolved["selected_main_model"] == "workspace-main"
    assert resolved["selected_lite_model"] == "workspace-lite"
    assert resolved["selected_coding_model"] == "workspace-main"
    assert resolved["temperature"] == 0.2
    assert resolved["allow_llm_data_samples"] is True
