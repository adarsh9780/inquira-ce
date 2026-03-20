from app.services import llm_provider_catalog


def test_provider_catalog_ignores_toml_model_overrides(monkeypatch, tmp_path):
    cfg_path = tmp_path / "inquira.toml"
    cfg_path.write_text(
        "\n".join(
            [
                "[llm.providers.openrouter]",
                'main-models = ["acme/private-main"]',
                'lite-models = ["acme/private-lite"]',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("INQUIRA_TOML_PATH", str(cfg_path))
    llm_provider_catalog._get_merged_catalogs.cache_clear()

    catalog = llm_provider_catalog.provider_model_catalog("openrouter")
    all_catalogs = llm_provider_catalog.all_provider_model_catalogs()

    assert "acme/private-main" not in catalog["main_models"]
    assert "acme/private-lite" not in catalog["lite_models"]
    assert "openrouter/free" in catalog["main_models"]
    assert all_catalogs["openrouter"]["main_models"] == catalog["main_models"]
    assert all_catalogs["openrouter"]["lite_models"] == catalog["lite_models"]
