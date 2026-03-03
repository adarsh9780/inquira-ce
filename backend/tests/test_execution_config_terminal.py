from app.services.execution_config import load_execution_runtime_config


def test_terminal_enabled_defaults_to_false(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text("[execution]\nprovider = 'local_jupyter'\n", encoding="utf-8")
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    monkeypatch.delenv("INQUIRA_TERMINAL_ENABLE", raising=False)
    load_execution_runtime_config.cache_clear()

    runtime = load_execution_runtime_config()
    assert runtime.terminal_enabled is False


def test_terminal_enabled_reads_from_toml_and_env_override(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        "[execution]\nprovider = 'local_jupyter'\n[terminal]\nenable = true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    load_execution_runtime_config.cache_clear()
    runtime = load_execution_runtime_config()
    assert runtime.terminal_enabled is True

    monkeypatch.setenv("INQUIRA_TERMINAL_ENABLE", "false")
    load_execution_runtime_config.cache_clear()
    runtime = load_execution_runtime_config()
    assert runtime.terminal_enabled is False


def test_plotly_theme_mode_reads_from_toml(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        "[execution]\nprovider = 'local_jupyter'\n[ui]\nplotly-theme-mode = 'hard'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    load_execution_runtime_config.cache_clear()

    runtime = load_execution_runtime_config()
    assert runtime.plotly_theme_mode == "hard"


def test_plotly_theme_mode_invalid_value_falls_back_to_soft(monkeypatch, tmp_path):
    cfg = tmp_path / "inquira.toml"
    cfg.write_text(
        "[execution]\nprovider = 'local_jupyter'\n[ui]\nplotly-theme-mode = 'loud'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg))
    load_execution_runtime_config.cache_clear()

    runtime = load_execution_runtime_config()
    assert runtime.plotly_theme_mode == "soft"
