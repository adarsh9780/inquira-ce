"""OS keychain backed secret storage helpers."""

from __future__ import annotations

import importlib


class SecretStorageService:
    """Store/retrieve secrets in the host OS keychain."""

    SERVICE_NAME = "com.inquira.api"

    @staticmethod
    def _account_for_user(user_id: str) -> str:
        return f"v1-user:{user_id}"

    @staticmethod
    def _load_keyring():
        try:
            return importlib.import_module("keyring")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Secure storage backend is unavailable. Install the 'keyring' package to enable OS keychain storage."
            ) from exc

    @staticmethod
    def set_api_key(user_id: str, api_key: str) -> None:
        keyring = SecretStorageService._load_keyring()
        account = SecretStorageService._account_for_user(user_id)
        keyring.set_password(SecretStorageService.SERVICE_NAME, account, api_key)

    @staticmethod
    def get_api_key(user_id: str) -> str | None:
        keyring = SecretStorageService._load_keyring()
        account = SecretStorageService._account_for_user(user_id)
        value = keyring.get_password(SecretStorageService.SERVICE_NAME, account)
        return (value or "").strip() or None

    @staticmethod
    def delete_api_key(user_id: str) -> None:
        keyring = SecretStorageService._load_keyring()
        account = SecretStorageService._account_for_user(user_id)
        try:
            keyring.delete_password(SecretStorageService.SERVICE_NAME, account)
        except Exception as exc:  # noqa: BLE001
            # Mirror prior behavior: deleting a non-existent key should be a no-op.
            if exc.__class__.__name__ == "PasswordDeleteError":
                return
            raise
