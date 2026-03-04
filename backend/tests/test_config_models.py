import importlib
import json


def test_load_merged_config_does_not_create_user_config_file(monkeypatch, tmp_path):
    from app.core import config_models as config_models_module

    config_models_module = importlib.reload(config_models_module)

    fake_home = tmp_path / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        config_models_module.Path, "home", staticmethod(lambda: fake_home)
    )

    default_cfg_path = tmp_path / "app_config.json"
    default_cfg_path.write_text(
        json.dumps(
            {
                "SECURE": True,
                "LOGGING": {
                    "console_level": "ERROR",
                    "file_level": "DEBUG",
                    "color_errors": True,
                    "uvicorn_access_log": True,
                    "uvicorn_log_level": "info",
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = config_models_module.AppConfig.load_merged_config(str(default_cfg_path))
    assert loaded.SECURE is True
    assert (fake_home / ".inquira" / "config.json").exists() is False
