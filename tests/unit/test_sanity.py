import pytest
from inquira.config_models import AppConfig

def test_app_config_defaults():
    config = AppConfig()
    assert config.SECURE is False
