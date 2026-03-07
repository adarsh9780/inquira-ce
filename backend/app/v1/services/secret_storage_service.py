"""OS keychain backed secret storage helpers."""

from __future__ import annotations

import importlib

from ...services.llm_provider_catalog import normalize_llm_provider


class SecretStorageService:
    """Store/retrieve secrets in the host OS keychain."""

    SERVICE_NAME = "com.inquira.api"

    @staticmethod
    def _legacy_account_for_user(user_id: str) -> str:
        return f"v1-user:{user_id}"

    @staticmethod
    def _account_for_user(user_id: str, provider: str) -> str:
        normalized_provider = normalize_llm_provider(provider)
        return f"v1-user:{user_id}:provider:{normalized_provider}"

    @staticmethod
    def _load_keyring():
        try:
            return importlib.import_module("keyring")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "Secure storage backend is unavailable. Install the 'keyring' package to enable OS keychain storage."
            ) from exc

    @staticmethod
    def set_api_key(user_id: str, api_key: str, provider: str = "openrouter") -> None:
        keyring = SecretStorageService._load_keyring()
        account = SecretStorageService._account_for_user(user_id, provider)
        keyring.set_password(SecretStorageService.SERVICE_NAME, account, api_key)

    @staticmethod
    def get_api_key(user_id: str, provider: str = "openrouter") -> str | None:
        keyring = SecretStorageService._load_keyring()
        normalized_provider = normalize_llm_provider(provider)
        account = SecretStorageService._account_for_user(user_id, normalized_provider)
        value = (keyring.get_password(SecretStorageService.SERVICE_NAME, account) or "").strip()
        if value:
            return value

        # Backward compatibility for older single-slot key storage.
        if normalized_provider == "openrouter":
            legacy_value = (
                keyring.get_password(
                    SecretStorageService.SERVICE_NAME,
                    SecretStorageService._legacy_account_for_user(user_id),
                )
                or ""
            ).strip()
            return legacy_value or None
        return None

    @staticmethod
    def delete_api_key(user_id: str, provider: str = "openrouter") -> None:
        keyring = SecretStorageService._load_keyring()
        normalized_provider = normalize_llm_provider(provider)
        account = SecretStorageService._account_for_user(user_id, normalized_provider)
        try:
            keyring.delete_password(SecretStorageService.SERVICE_NAME, account)
        except Exception as exc:  # noqa: BLE001
            # Mirror prior behavior: deleting a non-existent key should be a no-op.
            if exc.__class__.__name__ == "PasswordDeleteError":
                if normalized_provider != "openrouter":
                    return
            else:
                raise

        if normalized_provider != "openrouter":
            return

        # Remove legacy openrouter slot as well, if present.
        try:
            keyring.delete_password(
                SecretStorageService.SERVICE_NAME,
                SecretStorageService._legacy_account_for_user(user_id),
            )
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ == "PasswordDeleteError":
                return
            raise

    @staticmethod
    def get_api_key_presence_map(
        user_id: str,
        providers: list[str],
    ) -> dict[str, bool]:
        presence: dict[str, bool] = {}
        for provider in providers:
            normalized = normalize_llm_provider(provider)
            presence[normalized] = bool(SecretStorageService.get_api_key(user_id, normalized))
        return presence
