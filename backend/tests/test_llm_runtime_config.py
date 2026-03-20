import pytest

from app.services.llm_runtime_config import load_llm_runtime_config, normalize_model_id


def test_llm_runtime_config_reads_base_url_and_limits_from_toml_but_ignores_model_fields(
    monkeypatch, tmp_path
):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "http://localhost:4000/v1"',
                'default-model = "openai/gpt-4o-mini"',
                'lite-model = "openai/gpt-4.1-nano"',
                'models = ["acme/private-model"]',
                "[llm.limits]",
                "default = 2048",
                "schema = 1024",
                "code_generation = 3072",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()
    cfg = load_llm_runtime_config()

    assert cfg.provider == "openrouter"
    assert cfg.requires_api_key is True
    assert cfg.base_url == "http://localhost:4000/v1"
    assert cfg.default_model == "google/gemini-2.5-flash"
    assert cfg.lite_model == "google/gemini-2.5-flash-lite"
    assert cfg.default_max_tokens == 2048
    assert cfg.schema_max_tokens == 1024
    assert cfg.code_generation_max_tokens == 3072
    assert "acme/private-model" not in cfg.supported_models


def test_llm_runtime_config_env_overrides_toml(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                'default-model = "google/gemini-2.5-flash"',
                'lite-model = "google/gemini-2.5-flash-lite"',
                'models = ["acme/private-model"]',
                "[llm.limits]",
                "default = 4096",
                "schema = 2048",
                "code_generation = 4096",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    monkeypatch.setenv("INQUIRA_LLM_BASE_URL", "http://127.0.0.1:4000/v1")
    monkeypatch.setenv("INQUIRA_LLM_DEFAULT_MODEL", "gemini-3-flash-preview")
    monkeypatch.setenv("INQUIRA_LLM_LITE_MODEL", "openai/gpt-4.1-nano")
    monkeypatch.setenv(
        "INQUIRA_LLM_MODELS", "openai/gpt-4o-mini,google/gemini-2.5-flash"
    )
    monkeypatch.setenv("INQUIRA_LLM_DEFAULT_MAX_TOKENS", "1024")
    monkeypatch.setenv("INQUIRA_LLM_SCHEMA_MAX_TOKENS", "1536")
    monkeypatch.setenv("INQUIRA_LLM_CODE_MAX_TOKENS", "8192")
    load_llm_runtime_config.cache_clear()
    cfg = load_llm_runtime_config()

    assert cfg.base_url == "http://127.0.0.1:4000/v1"
    assert cfg.requires_api_key is True
    assert cfg.default_model == "google/gemini-3-flash-preview"
    assert cfg.lite_model == "openai/gpt-4.1-nano"
    assert cfg.default_max_tokens == 1024
    assert cfg.schema_max_tokens == 1536
    assert cfg.code_generation_max_tokens == 8192
    assert set(
        (
            "openai/gpt-4o-mini",
            "google/gemini-2.5-flash",
            "google/gemini-3-flash-preview",
            "openai/gpt-4.1-nano",
        )
    ).issubset(set(cfg.supported_models))


def test_normalize_model_id_supports_short_aliases():
    assert (
        normalize_model_id("gemini-3-flash-preview") == "google/gemini-3-flash-preview"
    )
    assert normalize_model_id("gemini-2.5-flash") == "google/gemini-2.5-flash"
    assert normalize_model_id("gemini-2.5-flash-lite") == "google/gemini-2.5-flash-lite"
    assert normalize_model_id("openrouter/free") == "openrouter/free"


def test_llm_runtime_config_ignores_toml_shorthand_model_ids(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'default-model = "gemini-2.5-flash"',
                'lite-model = "gemini-2.5-flash-lite"',
                'models = ["gemini-2.5-flash"]',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()
    cfg = load_llm_runtime_config()

    assert cfg.default_model == "google/gemini-2.5-flash"
    assert cfg.lite_model == "google/gemini-2.5-flash-lite"


def test_llm_runtime_config_rejects_non_positive_default_max_tokens(
    monkeypatch, tmp_path
):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                "[llm.limits]",
                "default = 0",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()

    with pytest.raises(ValueError, match="must be a positive integer"):
        load_llm_runtime_config()


def test_llm_runtime_config_rejects_non_positive_schema_or_code_limits(
    monkeypatch, tmp_path
):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                "[llm.limits]",
                "default = 4096",
                "schema = -1",
                "code_generation = 4096",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()

    with pytest.raises(ValueError, match="must be a positive integer"):
        load_llm_runtime_config()


def test_llm_runtime_config_rejects_shorthand_ids_in_env_models_list(monkeypatch):
    monkeypatch.setenv("INQUIRA_LLM_MODELS", "gemini-2.5-flash")
    load_llm_runtime_config.cache_clear()

    with pytest.raises(ValueError, match="must use the full model ID"):
        load_llm_runtime_config()


def test_runtime_config_ollama_no_api_key(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "ollama"',
                'base-url = "http://localhost:11434/v1"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()
    cfg = load_llm_runtime_config()

    assert cfg.provider == "ollama"
    assert cfg.requires_api_key is False
