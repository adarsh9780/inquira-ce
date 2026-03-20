from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.services.provider_model_refresh import ProviderRefreshResult, refresh_provider_model_catalog
from app.v1.api.preferences import refresh_provider_models
from app.v1.schemas.preferences import ProviderModelsRefreshRequest


@pytest.mark.asyncio
async def test_refresh_service_openrouter_falls_back_when_account_models_missing(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("unexpected status")

        def json(self):
            return self._payload

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, url, *args, **kwargs):
            _ = args, kwargs
            if url.endswith("/models"):
                return _Resp(
                    200,
                    {
                        "data": [
                            {"id": "openai/gpt-4o-mini"},
                            {"id": "google/gemini-2.5-flash"},
                        ]
                    },
                )
            if url.endswith("/auth/key"):
                return _Resp(200, {"data": {}})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("openrouter", api_key="sk-or-test")

    assert refreshed.catalog["main_models"] == ["openrouter/free"]
    assert refreshed.catalog["default_main_model"] == "openrouter/free"
    assert refreshed.catalog["account_models_configured"] is False
    assert "openrouter/free" in refreshed.detail


@pytest.mark.asyncio
async def test_refresh_endpoint_persists_catalog_and_returns_updated_preferences(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="openrouter/free",
        selected_lite_model="openrouter/free",
        selected_coding_model="openrouter/free",
        enabled_main_models_json='["openrouter/free"]',
        provider_model_catalogs_json="{}",
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

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None):
        _ = api_key
        return ProviderRefreshResult(
            provider="openrouter",
            detail="Refreshed OpenRouter account models.",
            catalog={
                "main_models": ["openai/gpt-4o-mini", "openrouter/free"],
                "lite_models": ["openrouter/free"],
                "default_main_model": "openai/gpt-4o-mini",
                "default_lite_model": "openrouter/free",
                "source": "refreshed",
                "account_models_configured": True,
                "account_models_url": "https://openrouter.ai/settings",
            },
        )

    monkeypatch.setattr(
        "app.v1.api.preferences.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences.refresh_provider_model_catalog",
        _fake_refresh_provider_model_catalog,
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

    response = await refresh_provider_models(
        ProviderModelsRefreshRequest(provider="openrouter", api_key="sk-or-test"),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    persisted_catalogs = json.loads(prefs.provider_model_catalogs_json)
    assert "openrouter" in persisted_catalogs
    assert persisted_catalogs["openrouter"]["main_models"] == [
        "openai/gpt-4o-mini",
        "openrouter/free",
    ]
    assert response.provider_available_main_models == [
        "openai/gpt-4o-mini",
        "openrouter/free",
    ]
    assert response.selected_model == "openrouter/free"
    assert response.detail == "Refreshed OpenRouter account models."
