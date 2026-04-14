from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api.preferences import update_preferences
from app.v1.schemas.preferences import PreferencesUpdateRequest
from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_update_preferences_persists_llm_advanced_settings(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        enabled_main_models_json='["google/gemini-2.5-flash"]',
        provider_model_catalogs_json="{}",
        llm_temperature=0.0,
        llm_max_tokens=2048,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
        schema_context="",
        allow_schema_sample_values=False,
        terminal_risk_acknowledged=False,
        chat_overlay_width=0.25,
        is_sidebar_collapsed=True,
        hide_shortcuts_modal=False,
        active_workspace_id=None,
        active_dataset_path=None,
        active_table_name=None,
    )

    class _Session:
        async def commit(self):
            return None

    async def _fake_get_or_create(_session, _principal_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.api.preferences.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences.SecretStorageService.get_api_key_presence_map",
        lambda _user_id, _providers: {
            "openrouter": True,
            "openai": False,
            "anthropic": False,
            "ollama": False,
        },
    )

    response = await update_preferences(
        PreferencesUpdateRequest(
            llm_temperature=0.3,
            llm_max_tokens=1024,
            llm_top_p=0.85,
            llm_top_k=24,
            llm_frequency_penalty=0.4,
            llm_presence_penalty=-0.2,
        ),
        session=_Session(),
        current_user=SimpleNamespace(id="user-1"),
    )

    assert prefs.llm_temperature == 0.3
    assert prefs.llm_max_tokens == 1024
    assert prefs.llm_top_p == 0.85
    assert prefs.llm_top_k == 24
    assert prefs.llm_frequency_penalty == 0.4
    assert prefs.llm_presence_penalty == -0.2
    assert response.llm_temperature == 0.3
    assert response.llm_max_tokens == 1024
    assert response.llm_top_p == 0.85
    assert response.llm_top_k == 24
    assert response.llm_frequency_penalty == 0.4
    assert response.llm_presence_penalty == -0.2


@pytest.mark.asyncio
async def test_chat_service_requires_advanced_llm_preferences(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        llm_temperature=0.1,
        llm_max_tokens=None,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
    )

    async def _fake_get_or_create(_session, _principal_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.services.chat_service.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )

    with pytest.raises(HTTPException) as exc_info:
        await ChatService._resolve_llm_preferences(SimpleNamespace(), "user-1")

    assert exc_info.value.status_code == 400
    assert "llm_max_tokens" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_chat_service_requires_top_k_preference(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        llm_temperature=0.1,
        llm_max_tokens=1024,
        llm_top_p=1.0,
        llm_top_k=None,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
    )

    async def _fake_get_or_create(_session, _principal_id):
        return prefs

    monkeypatch.setattr(
        "app.v1.services.chat_service.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )

    with pytest.raises(HTTPException) as exc_info:
        await ChatService._resolve_llm_preferences(SimpleNamespace(), "user-1")

    assert exc_info.value.status_code == 400
    assert "llm_top_k" in str(exc_info.value.detail)
