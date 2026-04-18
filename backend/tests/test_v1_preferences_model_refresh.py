from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import httpx

from app.services.provider_model_refresh import ProviderRefreshResult, refresh_provider_model_catalog
from app.v1.api.preferences import (
    _coerce_provider_catalog,
    refresh_provider_models,
    set_api_key,
    verify_api_key,
)
from app.v1.schemas.preferences import ApiKeyUpdateRequest, ApiKeyVerifyRequest, ProviderModelsRefreshRequest


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

    assert refreshed.catalog["main_models"] == ["openrouter/free"]
    assert refreshed.catalog["default_main_model"] == "openrouter/free"
    assert refreshed.catalog["account_models_configured"] is False
    assert "openrouter/free" in refreshed.detail


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
        "openai/gpt-4o-mini",
        "openrouter/free",
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

    monkeypatch.setattr(
        "app.v1.api.preferences.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )
    monkeypatch.setattr(
        "app.v1.api.preferences.SecretStorageService.set_api_key",
        _fake_set_api_key,
    )

    response = await set_api_key(
        ApiKeyUpdateRequest(
            provider="openrouter",
            api_key="sk-test",
            selected_model="openai/gpt-4o",
            selected_lite_model="google/gemini-2.0-flash-001",
            selected_coding_model="openai/gpt-4o",
            enabled_models=["openai/gpt-4o"],
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
    assert "Configuration and API key" in response.message


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

    monkeypatch.setattr(
        "app.v1.api.preferences.PreferencesRepository.get_or_create",
        _fake_get_or_create,
    )

    await set_api_key(
        ApiKeyUpdateRequest(
            provider="ollama",
            base_url="http://localhost:11434/api",
            selected_model="llama3.2",
            selected_lite_model="llama3.2:3b",
            enabled_models=["llama3.2"],
        ),
        session=_Session(),
        current_user=SimpleNamespace(id="u1"),
    )

    persisted_catalogs = json.loads(prefs.provider_model_catalogs_json)
    assert persisted_catalogs["ollama"]["base_url"] == "http://localhost:11434/api"


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
