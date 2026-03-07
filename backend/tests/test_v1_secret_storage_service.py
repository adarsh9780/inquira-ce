from __future__ import annotations

import sys
from types import SimpleNamespace

from app.v1.services.secret_storage_service import SecretStorageService


def test_secret_storage_service_uses_keyring_module(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    class PasswordDeleteError(Exception):
        pass

    def set_password(service: str, account: str, secret: str) -> None:
        store[(service, account)] = secret

    def get_password(service: str, account: str) -> str | None:
        return store.get((service, account))

    def delete_password(service: str, account: str) -> None:
        key = (service, account)
        if key not in store:
            raise PasswordDeleteError("missing")
        del store[key]

    fake_keyring = SimpleNamespace(
        set_password=set_password,
        get_password=get_password,
        delete_password=delete_password,
        errors=SimpleNamespace(PasswordDeleteError=PasswordDeleteError),
    )
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)

    SecretStorageService.set_api_key("u1", "secret-openrouter", provider="openrouter")
    SecretStorageService.set_api_key("u1", "secret-openai", provider="openai")
    assert SecretStorageService.get_api_key("u1", provider="openrouter") == "secret-openrouter"
    assert SecretStorageService.get_api_key("u1", provider="openai") == "secret-openai"
    assert SecretStorageService.get_api_key("u1", provider="anthropic") is None

    presence = SecretStorageService.get_api_key_presence_map(
        "u1", ["openrouter", "openai", "anthropic", "ollama"]
    )
    assert presence == {
        "openrouter": True,
        "openai": True,
        "anthropic": False,
        "ollama": False,
    }

    SecretStorageService.delete_api_key("u1", provider="openai")
    assert SecretStorageService.get_api_key("u1", provider="openai") is None

    SecretStorageService.delete_api_key("u1", provider="openrouter")
    assert SecretStorageService.get_api_key("u1", provider="openrouter") is None

    # Deleting again should be safe.
    SecretStorageService.delete_api_key("u1", provider="openrouter")


def test_secret_storage_service_supports_legacy_openrouter_slot(monkeypatch):
    store: dict[tuple[str, str], str] = {}

    class PasswordDeleteError(Exception):
        pass

    def set_password(service: str, account: str, secret: str) -> None:
        store[(service, account)] = secret

    def get_password(service: str, account: str) -> str | None:
        return store.get((service, account))

    def delete_password(service: str, account: str) -> None:
        key = (service, account)
        if key not in store:
            raise PasswordDeleteError("missing")
        del store[key]

    fake_keyring = SimpleNamespace(
        set_password=set_password,
        get_password=get_password,
        delete_password=delete_password,
        errors=SimpleNamespace(PasswordDeleteError=PasswordDeleteError),
    )
    monkeypatch.setitem(sys.modules, "keyring", fake_keyring)

    # Simulate pre-migration single-slot key.
    store[(SecretStorageService.SERVICE_NAME, "v1-user:u2")] = "legacy-key"
    assert SecretStorageService.get_api_key("u2", provider="openrouter") == "legacy-key"
