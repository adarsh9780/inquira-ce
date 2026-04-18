from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import httpx

from app.services.provider_model_refresh import ProviderModelRefreshError, ProviderRefreshResult, refresh_provider_model_catalog
from app.v1.api.preferences import (
    _coerce_provider_catalog,
    _to_response,
    search_provider_models,
    refresh_provider_models,
    set_api_key,
    verify_api_key,
)
from app.v1.schemas.preferences import ApiKeyUpdateRequest, ApiKeyVerifyRequest, ApiKeyVerifyResponse, ProviderModelsRefreshRequest


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
            if url.endswith("/models/user"):
                return _Resp(200, {"data": []})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("openrouter", api_key="sk-or-test")

    assert refreshed.catalog["main_models"] == [
        "google/gemini-2.5-flash",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4-5",
    ]
    assert refreshed.catalog["default_main_model"] == "google/gemini-2.5-flash"
    assert refreshed.catalog["account_models_configured"] is False
    assert "Using curated OpenRouter defaults" in refreshed.detail


@pytest.mark.asyncio
async def test_refresh_service_openrouter_uses_user_filtered_models(monkeypatch):
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
            if url.endswith("/models/user"):
                return _Resp(
                    200,
                    {
                        "data": [
                            {"id": "openai/gpt-4o-mini"},
                            {"id": "anthropic/claude-3.5-sonnet"},
                        ]
                    },
                )
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("openrouter", api_key="sk-or-test")

    assert refreshed.catalog["main_models"] == [
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet",
    ]
    assert refreshed.catalog["account_models_configured"] is True
    assert "Refreshed 2 OpenRouter account models." == refreshed.detail


@pytest.mark.asyncio
async def test_preferences_response_injects_selected_openrouter_model_into_display_list():
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="mistralai/mixtral-8x7b",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="mistralai/mixtral-8x7b",
        enabled_main_models_json='["google/gemini-2.5-flash"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openrouter": {
                    "main_models": [
                        "google/gemini-2.5-flash",
                        "openai/gpt-4o",
                        "anthropic/claude-sonnet-4-5",
                        "mistralai/mixtral-8x7b",
                        "deepseek/deepseek-chat",
                        "meta-llama/llama-3.3-70b-instruct",
                    ],
                    "lite_models": ["google/gemini-2.5-flash-lite"],
                    "default_main_model": "google/gemini-2.5-flash",
                    "default_lite_model": "google/gemini-2.5-flash-lite",
                    "source": "bundled",
                    "models": [
                        {"id": "google/gemini-2.5-flash", "display_name": "Gemini 2.5 Flash"},
                        {"id": "openai/gpt-4o", "display_name": "GPT-4o"},
                        {"id": "anthropic/claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5"},
                        {"id": "mistralai/mixtral-8x7b", "display_name": "Mixtral 8x7B"},
                        {"id": "deepseek/deepseek-chat", "display_name": "DeepSeek Chat"},
                        {"id": "meta-llama/llama-3.3-70b-instruct", "display_name": "Llama 3.3 70B"},
                    ],
                }
            }
        ),
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

    response = _to_response(
        prefs,
        {
            "openrouter": False,
            "openai": False,
            "anthropic": False,
            "ollama": False,
        },
    )

    assert response.selected_model == "mistralai/mixtral-8x7b"
    assert response.provider_available_main_models == [
        "mistralai/mixtral-8x7b",
        "google/gemini-2.5-flash",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4-5",
    ]
    assert "deepseek/deepseek-chat" not in response.provider_available_main_models
    assert "meta-llama/llama-3.3-70b-instruct" not in response.provider_available_main_models
    assert response.provider_model_catalogs["openrouter"].main_models == [
        "google/gemini-2.5-flash",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4-5",
        "mistralai/mixtral-8x7b",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
    ]


@pytest.mark.asyncio
async def test_preferences_response_limits_openrouter_display_list_to_100_and_keeps_selected_model():
    curated_models = [f"google/model-{index:03d}" for index in range(1, 121)]
    full_catalog = [
        *curated_models,
        "mistralai/mixtral-8x7b",
    ]

    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="mistralai/mixtral-8x7b",
        selected_lite_model="google/model-001",
        selected_coding_model="mistralai/mixtral-8x7b",
        enabled_main_models_json='["google/model-001"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openrouter": {
                    "main_models": full_catalog,
                    "lite_models": ["google/model-001"],
                    "default_main_model": "google/model-001",
                    "default_lite_model": "google/model-001",
                    "source": "bundled",
                    "models": [{"id": model_id, "display_name": model_id} for model_id in full_catalog],
                }
            }
        ),
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

    response = _to_response(
        prefs,
        {
            "openrouter": False,
            "openai": False,
            "anthropic": False,
            "ollama": False,
        },
    )

    assert len(response.provider_available_main_models) == 100
    assert response.provider_available_main_models[0] == "mistralai/mixtral-8x7b"
    assert "google/model-100" not in response.provider_available_main_models
    assert response.provider_model_catalogs["openrouter"].main_models == full_catalog


@pytest.mark.asyncio
async def test_search_provider_models_returns_full_openrouter_catalog_entries(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        enabled_main_models_json='["google/gemini-2.5-flash"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openrouter": {
                    "main_models": [
                        "google/gemini-2.5-flash",
                        "openai/gpt-4o",
                        "anthropic/claude-sonnet-4-5",
                        "mistralai/mixtral-8x7b",
                        "deepseek/deepseek-chat",
                    ],
                    "lite_models": ["google/gemini-2.5-flash-lite"],
                    "default_main_model": "google/gemini-2.5-flash",
                    "default_lite_model": "google/gemini-2.5-flash-lite",
                    "source": "bundled",
                    "models": [
                        {"id": "google/gemini-2.5-flash", "display_name": "Gemini 2.5 Flash", "tags": ["recommended"]},
                        {"id": "openai/gpt-4o", "display_name": "GPT-4o", "tags": ["recommended"]},
                        {"id": "anthropic/claude-sonnet-4-5", "display_name": "Claude Sonnet 4.5", "tags": ["recommended"]},
                        {"id": "mistralai/mixtral-8x7b", "display_name": "Mixtral 8x7B", "tags": ["extended"]},
                        {"id": "deepseek/deepseek-chat", "display_name": "DeepSeek Chat", "tags": ["extended"]},
                    ],
                }
            }
        ),
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

    response = await search_provider_models(
        provider="openrouter",
        q="deepseek",
        limit=25,
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    assert response.provider == "openrouter"
    assert response.query == "deepseek"
    assert [item.id for item in response.models] == ["deepseek/deepseek-chat"]


@pytest.mark.asyncio
async def test_search_provider_models_ignores_short_queries(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        enabled_main_models_json='["google/gemini-2.5-flash"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openrouter": {
                    "main_models": ["google/gemini-2.5-flash", "mistralai/mixtral-8x7b"],
                    "lite_models": ["google/gemini-2.5-flash-lite"],
                    "default_main_model": "google/gemini-2.5-flash",
                    "default_lite_model": "google/gemini-2.5-flash-lite",
                    "source": "bundled",
                    "models": [
                        {"id": "google/gemini-2.5-flash", "display_name": "Gemini 2.5 Flash"},
                        {"id": "mistralai/mixtral-8x7b", "display_name": "Mixtral 8x7B"},
                    ],
                }
            }
        ),
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

    response = await search_provider_models(
        provider="openrouter",
        q="g",
        limit=25,
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    assert response.models == []


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

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None, base_url: str | None = None):
        _ = api_key, base_url
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
        "openrouter/free",
        "openai/gpt-4o-mini",
    ]
    assert response.selected_model == "openrouter/free"
    assert response.detail == "Refreshed OpenRouter account models."


@pytest.mark.asyncio
async def test_set_api_key_endpoint_persists_models_and_advanced_settings(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="openrouter/free",
        selected_lite_model="openrouter/free",
        selected_coding_model="openrouter/free",
        enabled_main_models_json='["openrouter/free"]',
        provider_model_catalogs_json="{}",
        llm_temperature=0.7,
        llm_max_tokens=4096,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
        slow_request_warning_seconds=30,
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
    captured_secret_write: dict[str, str] = {}

    class _Session:
        async def commit(self):
            return None

    async def _fake_get_or_create(_session, _principal_id):
        return prefs

    def _fake_set_api_key(_user_id, key, provider="openrouter"):
        captured_secret_write["key"] = key
        captured_secret_write["provider"] = provider

    async def _fake_verify_provider_api_key(_provider: str, _api_key: str):
        return ApiKeyVerifyResponse(valid=True, error="")

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None, base_url: str | None = None):
        _ = api_key, base_url
        return ProviderRefreshResult(
            provider="openrouter",
            detail="Refreshed 2 OpenRouter account models.",
            catalog={
                "main_models": ["openai/gpt-4o", "openrouter/free"],
                "lite_models": ["google/gemini-2.0-flash-001", "openrouter/free"],
                "default_main_model": "openai/gpt-4o",
                "default_lite_model": "google/gemini-2.0-flash-001",
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
        "app.v1.api.preferences.SecretStorageService.set_api_key",
        _fake_set_api_key,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences._verify_provider_api_key",
        _fake_verify_provider_api_key,
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

    response = await set_api_key(
        ApiKeyUpdateRequest(
            provider="openrouter",
            api_key="sk-test",
            selected_model="openai/gpt-4o",
            selected_lite_model="google/gemini-2.0-flash-001",
            selected_coding_model="openai/gpt-4o",
            llm_temperature=0.9,
            llm_max_tokens=3072,
            llm_top_p=0.8,
            llm_top_k=32,
            llm_frequency_penalty=0.1,
            llm_presence_penalty=0.2,
            slow_request_warning_seconds=45,
        ),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    assert prefs.llm_provider == "openrouter"
    assert prefs.selected_model == "openai/gpt-4o"
    assert prefs.selected_lite_model == "google/gemini-2.0-flash-001"
    assert prefs.selected_coding_model == "openai/gpt-4o"
    assert prefs.llm_temperature == 0.9
    assert prefs.llm_max_tokens == 3072
    assert prefs.llm_top_p == 0.8
    assert prefs.llm_top_k == 32
    assert prefs.llm_frequency_penalty == 0.1
    assert prefs.llm_presence_penalty == 0.2
    assert prefs.slow_request_warning_seconds == 45
    assert captured_secret_write == {"key": "sk-test", "provider": "openrouter"}
    assert response.detail == "Refreshed 2 OpenRouter account models."
    assert response.warning == ""


@pytest.mark.asyncio
async def test_set_api_key_endpoint_warns_when_model_refresh_fails_after_key_save(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openrouter",
        selected_model="google/gemini-2.5-flash",
        selected_lite_model="google/gemini-2.5-flash-lite",
        selected_coding_model="google/gemini-2.5-flash",
        enabled_main_models_json='["google/gemini-2.5-flash"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openrouter": {
                    "main_models": ["google/gemini-2.5-flash", "openrouter/free"],
                    "lite_models": ["google/gemini-2.5-flash-lite"],
                    "default_main_model": "google/gemini-2.5-flash",
                    "default_lite_model": "google/gemini-2.5-flash-lite",
                    "source": "bundled",
                    "models": [
                        {"id": "google/gemini-2.5-flash", "display_name": "Gemini 2.5 Flash"},
                        {"id": "openrouter/free", "display_name": "OpenRouter Free"},
                    ],
                }
            }
        ),
        llm_temperature=0.7,
        llm_max_tokens=4096,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
        slow_request_warning_seconds=30,
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
    captured_secret_write: dict[str, str] = {}

    class _Session:
        async def commit(self):
            return None

    async def _fake_get_or_create(_session, _principal_id):
        return prefs

    def _fake_set_api_key(_user_id, key, provider="openrouter"):
        captured_secret_write["key"] = key
        captured_secret_write["provider"] = provider

    async def _fake_verify_provider_api_key(_provider: str, _api_key: str):
        return ApiKeyVerifyResponse(valid=True, error="")

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None, base_url: str | None = None):
        _ = api_key, base_url
        raise ProviderModelRefreshError("provider refresh failed", status_code=502)

    monkeypatch.setattr(
        "app.v1.api.preferences.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences.SecretStorageService.set_api_key",
        _fake_set_api_key,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences._verify_provider_api_key",
        _fake_verify_provider_api_key,
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

    response = await set_api_key(
        ApiKeyUpdateRequest(
            provider="openrouter",
            api_key="sk-test",
        ),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    assert captured_secret_write == {"key": "sk-test", "provider": "openrouter"}
    assert response.warning == "API key saved, but model refresh failed. Using previous catalog."
    assert response.detail == "Configuration for provider 'openrouter' saved."


@pytest.mark.asyncio
async def test_set_api_key_endpoint_persists_ollama_base_url(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="ollama",
        selected_model="llama3.2",
        selected_lite_model="llama3.2:3b",
        selected_coding_model="llama3.2",
        enabled_main_models_json='["llama3.2"]',
        provider_model_catalogs_json=json.dumps(
            {
                "ollama": {
                    "main_models": ["llama3.2"],
                    "lite_models": ["llama3.2:3b"],
                    "default_main_model": "llama3.2",
                    "default_lite_model": "llama3.2:3b",
                    "base_url": "http://localhost:11434",
                }
            }
        ),
        llm_temperature=0.7,
        llm_max_tokens=4096,
        llm_top_p=1.0,
        llm_top_k=0,
        llm_frequency_penalty=0.0,
        llm_presence_penalty=0.0,
        slow_request_warning_seconds=30,
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

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None, base_url: str | None = None):
        _ = api_key, base_url
        return ProviderRefreshResult(
            provider="ollama",
            detail="Refreshed 1 Ollama models.",
            catalog={
                "main_models": ["llama3.2"],
                "lite_models": ["llama3.2:3b"],
                "default_main_model": "llama3.2",
                "default_lite_model": "llama3.2:3b",
                "source": "refreshed",
                "base_url": "http://localhost:11434/api",
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
            "openrouter": False,
            "openai": False,
            "anthropic": False,
            "ollama": False,
        },
    )

    response = await set_api_key(
        ApiKeyUpdateRequest(
            provider="ollama",
            base_url="http://localhost:11434/api",
            selected_model="llama3.2",
            selected_lite_model="llama3.2:3b",
        ),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    persisted_catalogs = json.loads(prefs.provider_model_catalogs_json)
    assert persisted_catalogs["ollama"]["base_url"] == "http://localhost:11434/api"
    assert response.detail == "Refreshed 1 Ollama models."


def test_coerce_provider_catalog_coerces_invalid_context_window_values():
    fallback = {
        "main_models": ["openrouter/free"],
        "lite_models": ["openrouter/free"],
        "default_main_model": "openrouter/free",
        "default_lite_model": "openrouter/free",
        "source": "bundled",
        "models": [],
    }

    catalog = _coerce_provider_catalog(
        "openrouter",
        {
            "main_models": ["openrouter/free", "openrouter/fast"],
            "lite_models": ["openrouter/free"],
            "default_main_model": "openrouter/free",
            "default_lite_model": "openrouter/free",
            "models": [
                {"id": "openrouter/free", "context_window": None},
                {"id": "openrouter/fast", "context_window": -512},
            ],
        },
        fallback,
    )

    models_by_id = {item["id"]: item for item in catalog["models"]}
    assert models_by_id["openrouter/free"]["context_window"] == 0
    assert models_by_id["openrouter/fast"]["context_window"] == 0


def test_coerce_provider_catalog_keeps_cloud_suffix_only_for_ollama():
    openrouter_fallback = {
        "main_models": ["openrouter/free"],
        "lite_models": ["openrouter/free"],
        "default_main_model": "openrouter/free",
        "default_lite_model": "openrouter/free",
        "source": "bundled",
        "models": [],
    }
    ollama_fallback = {
        "main_models": ["llama3.2"],
        "lite_models": ["llama3.2:3b"],
        "default_main_model": "llama3.2",
        "default_lite_model": "llama3.2:3b",
        "source": "bundled",
        "models": [],
    }

    openrouter_catalog = _coerce_provider_catalog(
        "openrouter",
        {
            "main_models": ["google/gemini-3-flash-preview:cloud", "openrouter/free"],
            "lite_models": ["google/gemini-3-flash-preview:cloud", "openrouter/free"],
            "default_main_model": "google/gemini-3-flash-preview:cloud",
            "default_lite_model": "google/gemini-3-flash-preview:cloud",
            "models": [
                {"id": "google/gemini-3-flash-preview:cloud", "context_window": 1000},
                {"id": "openrouter/free", "context_window": 1000},
            ],
        },
        openrouter_fallback,
    )
    ollama_catalog = _coerce_provider_catalog(
        "ollama",
        {
            "main_models": ["minimax-m2.7:cloud"],
            "lite_models": ["minimax-m2.7:cloud"],
            "default_main_model": "minimax-m2.7:cloud",
            "default_lite_model": "minimax-m2.7:cloud",
            "models": [{"id": "minimax-m2.7:cloud", "context_window": 1000}],
        },
        ollama_fallback,
    )

    assert openrouter_catalog["main_models"] == ["openrouter/free"]
    assert openrouter_catalog["lite_models"] == ["openrouter/free"]
    assert openrouter_catalog["default_main_model"] == "openrouter/free"
    assert [item["id"] for item in openrouter_catalog["models"]] == ["openrouter/free"]
    assert ollama_catalog["main_models"] == ["minimax-m2.7:cloud"]
    assert ollama_catalog["models"][0]["id"] == "minimax-m2.7:cloud"


@pytest.mark.asyncio
async def test_refresh_endpoint_preserves_existing_recommended_tags_when_merging(monkeypatch):
    prefs = SimpleNamespace(
        llm_provider="openai",
        selected_model="gpt-4.1",
        selected_lite_model="gpt-4.1-mini",
        selected_coding_model="gpt-4.1",
        enabled_main_models_json='["gpt-4.1"]',
        provider_model_catalogs_json=json.dumps(
            {
                "openai": {
                    "main_models": ["gpt-4.1"],
                    "lite_models": ["gpt-4.1-mini"],
                    "default_main_model": "gpt-4.1",
                    "default_lite_model": "gpt-4.1-mini",
                    "source": "bundled",
                    "models": [
                        {
                            "id": "gpt-4.1",
                            "display_name": "GPT-4.1",
                            "provider": "openai",
                            "context_window": 1047576,
                            "recommended_for": ["main"],
                            "tags": ["recommended"],
                        }
                    ],
                }
            }
        ),
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

    async def _fake_refresh_provider_model_catalog(_provider: str, api_key: str | None = None, base_url: str | None = None):
        _ = api_key, base_url
        return ProviderRefreshResult(
            provider="openai",
            detail="Refreshed OpenAI models.",
            catalog={
                "main_models": ["gpt-4.1", "gpt-5"],
                "lite_models": ["gpt-4.1-mini"],
                "default_main_model": "gpt-4.1",
                "default_lite_model": "gpt-4.1-mini",
                "source": "refreshed",
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
            "openrouter": False,
            "openai": True,
            "anthropic": False,
            "ollama": False,
        },
    )

    await refresh_provider_models(
        ProviderModelsRefreshRequest(provider="openai", api_key="sk-openai-test"),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    persisted_catalogs = json.loads(prefs.provider_model_catalogs_json)
    openai_models = persisted_catalogs["openai"]["models"]
    model_by_id = {item["id"]: item for item in openai_models}

    assert model_by_id["gpt-4.1"]["tags"] == ["recommended"]
    assert model_by_id["gpt-4.1"]["recommended_for"] == ["main"]
    assert model_by_id["gpt-5"]["tags"] == ["extended"]


@pytest.mark.asyncio
async def test_refresh_service_ollama_unreachable_returns_non_fatal_error(monkeypatch):
    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, _url, *args, **kwargs):
            _ = args, kwargs
            raise httpx.ConnectError("connection failed")

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("ollama", base_url="http://localhost:11434")

    assert refreshed.error == "ollama_unreachable"
    assert refreshed.catalog.get("source") == "default"


@pytest.mark.asyncio
async def test_refresh_service_ollama_merges_local_and_cloud_models(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.request = httpx.Request("GET", "https://example.test")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "status error",
                    request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

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
            if str(url).startswith("http://localhost:11434"):
                return _Resp(200, {"models": [{"name": "llama3.2"}]})
            if str(url) == "https://ollama.com/api/tags":
                return _Resp(200, {"models": [{"model": "gpt-oss:20b-cloud"}]})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("ollama", base_url="http://localhost:11434")

    assert refreshed.error == ""
    assert refreshed.catalog["main_models"] == ["llama3.2", "gpt-oss:20b-cloud"]
    assert "local + 1 cloud" in refreshed.detail


@pytest.mark.asyncio
async def test_refresh_service_ollama_accepts_model_field_from_tags(monkeypatch):
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
            if str(url).startswith("http://localhost:11434"):
                return _Resp(200, {"models": [{"model": "qwen3-coder:480b-cloud"}]})
            if str(url) == "https://ollama.com/api/tags":
                return _Resp(401, {})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("ollama", base_url="http://localhost:11434")

    assert refreshed.error == ""
    assert "qwen3-coder:480b-cloud" in refreshed.catalog["main_models"]


@pytest.mark.asyncio
async def test_refresh_service_ollama_prefers_model_field_over_name_field(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.request = httpx.Request("GET", "https://example.test")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "status error",
                    request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

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
            if str(url).startswith("http://localhost:11434"):
                return _Resp(
                    200,
                    {"models": [{"name": "minimax-m2.7", "model": "minimax-m2.7:cloud"}]},
                )
            if str(url) == "https://ollama.com/api/tags":
                return _Resp(401, {})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("ollama", base_url="http://localhost:11434")

    assert refreshed.error == ""
    assert refreshed.catalog["main_models"] == ["minimax-m2.7:cloud"]


@pytest.mark.asyncio
async def test_refresh_service_ollama_cloud_name_without_tag_normalizes_to_cloud_suffix(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.request = httpx.Request("GET", "https://example.test")

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "status error",
                    request=self.request,
                    response=httpx.Response(self.status_code, request=self.request),
                )

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
            if str(url).startswith("http://localhost:11434"):
                return _Resp(200, {"models": []})
            if str(url) == "https://ollama.com/api/tags":
                return _Resp(200, {"models": [{"name": "minimax-m2.7"}]})
            return _Resp(404, {})

    monkeypatch.setattr("app.services.provider_model_refresh.httpx.AsyncClient", _Client)

    refreshed = await refresh_provider_model_catalog("ollama", base_url="http://localhost:11434")

    assert refreshed.error == ""
    assert refreshed.catalog["main_models"] == ["minimax-m2.7:cloud"]


@pytest.mark.asyncio
async def test_verify_api_key_maps_provider_status_codes(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int):
            self.status_code = status_code

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, _url, *args, **kwargs):
            _ = args, kwargs
            return _Resp(429)

    monkeypatch.setattr("app.v1.api.preferences.httpx.AsyncClient", _Client)
    response = await verify_api_key(ApiKeyVerifyRequest(provider="openrouter", api_key="sk-or-test"))
    assert response.valid is False
    assert response.error == "quota_exceeded"


@pytest.mark.asyncio
async def test_verify_api_key_accepts_success_status(monkeypatch):
    class _Resp:
        def __init__(self, status_code: int):
            self.status_code = status_code

    class _Client:
        def __init__(self, *args, **kwargs):
            _ = args, kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return False

        async def get(self, _url, *args, **kwargs):
            _ = args, kwargs
            return _Resp(200)

    monkeypatch.setattr("app.v1.api.preferences.httpx.AsyncClient", _Client)
    response = await verify_api_key(ApiKeyVerifyRequest(provider="openai", api_key="sk-openai-test"))
    assert response.valid is True
    assert response.error == ""
