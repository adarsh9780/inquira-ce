import pytest

from app.services.llm_runtime_config import load_llm_runtime_config, normalize_model_id


def test_llm_runtime_config_reads_base_url_and_models_from_toml(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "http://localhost:4000/v1"',
                'default-model = "openai/gpt-4o-mini"',
                'lite-model = "openai/gpt-4.1-nano"',
                'models = ["openai/gpt-4o-mini", "openai/gpt-4.1-nano"]',
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
    assert cfg.base_url == "http://localhost:4000/v1"
    assert cfg.default_model == "openai/gpt-4o-mini"
    assert cfg.lite_model == "openai/gpt-4.1-nano"
    assert cfg.default_max_tokens == 2048
    assert cfg.schema_max_tokens == 1024
    assert cfg.code_generation_max_tokens == 3072
    assert cfg.supported_models == ("openai/gpt-4o-mini", "openai/gpt-4.1-nano")


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
                'models = ["google/gemini-2.5-flash"]',
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
    monkeypatch.setenv(
        "INQUIRA_LLM_MODELS", "openai/gpt-4o-mini,google/gemini-2.5-flash"
    )
    monkeypatch.setenv("INQUIRA_LLM_DEFAULT_MAX_TOKENS", "1024")
    monkeypatch.setenv("INQUIRA_LLM_SCHEMA_MAX_TOKENS", "1536")
    monkeypatch.setenv("INQUIRA_LLM_CODE_MAX_TOKENS", "8192")
    load_llm_runtime_config.cache_clear()
    cfg = load_llm_runtime_config()

    assert cfg.base_url == "http://127.0.0.1:4000/v1"
    assert cfg.default_model == "google/gemini-3-flash-preview"
    assert cfg.lite_model == "google/gemini-2.5-flash-lite"
    assert cfg.default_max_tokens == 1024
    assert cfg.schema_max_tokens == 1536
    assert cfg.code_generation_max_tokens == 8192
    assert cfg.supported_models == (
        "openai/gpt-4o-mini",
        "google/gemini-2.5-flash",
        "google/gemini-3-flash-preview",
        "google/gemini-2.5-flash-lite",
    )


def test_normalize_model_id_supports_short_aliases():
    assert normalize_model_id("gemini-3-flash-preview") == "google/gemini-3-flash-preview"
    assert normalize_model_id("gemini-2.5-flash") == "google/gemini-2.5-flash"
    assert normalize_model_id("gemini-2.5-flash-lite") == "google/gemini-2.5-flash-lite"
    assert normalize_model_id("openrouter/free") == "openrouter/free"


def test_llm_runtime_config_rejects_shorthand_model_ids_in_toml(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                'default-model = "gemini-2.5-flash"',
                'lite-model = "google/gemini-2.5-flash-lite"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()

    try:
        load_llm_runtime_config()
        raise AssertionError("Expected ValueError for shorthand model ID in TOML")
    except ValueError as exc:
        assert "must use the full model ID" in str(exc)


def test_llm_runtime_config_rejects_non_positive_default_max_tokens(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                'default-model = "google/gemini-2.5-flash"',
                'lite-model = "google/gemini-2.5-flash-lite"',
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


def test_llm_runtime_config_rejects_non_positive_schema_or_code_limits(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                'default-model = "google/gemini-2.5-flash"',
                'lite-model = "google/gemini-2.5-flash-lite"',
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


def test_llm_runtime_config_rejects_shorthand_ids_in_models_list(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm]",
                'provider = "openrouter"',
                'base-url = "https://openrouter.ai/api/v1"',
                'default-model = "google/gemini-2.5-flash"',
                'lite-model = "google/gemini-2.5-flash-lite"',
                'models = ["gemini-2.5-flash"]',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    load_llm_runtime_config.cache_clear()

    with pytest.raises(ValueError, match="must use the full model ID"):
        load_llm_runtime_config()
