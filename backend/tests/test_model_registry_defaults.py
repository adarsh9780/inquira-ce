from app.services.model_registry import (
    clear_model_registry_cache,
    load_bundled_model_registry,
    merge_refreshed_model_metadata,
    provider_catalog_from_registry,
)


def test_bundled_registry_loads_recommended_openai_and_openrouter_models():
    clear_model_registry_cache()
    payload = load_bundled_model_registry()

    assert payload.get("last_updated") == "2026-04-14"
    models = payload.get("models", [])
    providers = {item.get("provider") for item in models}

    assert "openai" in providers
    assert "openrouter" in providers
    assert "ollama" not in providers


def test_provider_catalog_from_registry_builds_main_and_lite_defaults():
    clear_model_registry_cache()
    openai_catalog = provider_catalog_from_registry("openai")

    assert "gpt-4.1" in openai_catalog["main_models"]
    assert "gpt-4.1-mini" in openai_catalog["lite_models"]
    assert openai_catalog["default_main_model"] == "gpt-4.1"
    assert openai_catalog["default_lite_model"] == "gpt-4.1-mini"


def test_merge_refreshed_model_metadata_coerces_invalid_context_window_values():
    merged = merge_refreshed_model_metadata(
        provider="openrouter",
        existing_entries=[
            {"id": "openrouter/free", "context_window": None},
            {"id": "openai/gpt-4.1-mini", "context_window": -10},
        ],
        refreshed_main_models=["openrouter/free"],
        refreshed_lite_models=["openai/gpt-4.1-mini"],
    )

    assert merged[0]["context_window"] == 0
    assert merged[1]["context_window"] == 0
