from app.services.model_registry import (
    clear_model_registry_cache,
    load_bundled_model_registry,
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
