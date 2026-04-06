from __future__ import annotations

from types import SimpleNamespace

from app.v1.api.preferences import _to_response


def test_preferences_response_treats_openrouter_env_key_as_present(monkeypatch):
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
        is_sidebar_collapsed=False,
        hide_shortcuts_modal=False,
        active_workspace_id=None,
        active_dataset_path=None,
        active_table_name=None,
    )

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr(
        "app.v1.api.preferences.load_execution_runtime_config",
        lambda: SimpleNamespace(plotly_theme_mode="light"),
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

    assert response.api_key_present is True
    assert response.selected_provider_api_key_present is True
    assert response.api_key_present_by_provider["openrouter"] is True
