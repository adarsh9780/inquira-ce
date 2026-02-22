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

    SecretStorageService.set_api_key("u1", "secret-123")
    assert SecretStorageService.get_api_key("u1") == "secret-123"
    SecretStorageService.delete_api_key("u1")
    assert SecretStorageService.get_api_key("u1") is None

    # Deleting again should be safe.
    SecretStorageService.delete_api_key("u1")
