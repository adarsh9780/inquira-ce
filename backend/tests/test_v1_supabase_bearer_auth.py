from types import SimpleNamespace
import json

import pytest
import jwt
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.requests import Request

from app.v1.core.settings import V1Settings
from app.v1.api.deps import get_current_user
from app.v1.services.auth_service import AuthService


def _request_with_headers(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/me",
        "headers": [
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in headers.items()
        ],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_get_current_user_uses_supabase_bearer_token(monkeypatch):
    async def fake_resolve(token: str):
        assert token == "token-123"
        return SimpleNamespace(id="user-1", username="alice@example.com", plan="FREE")

    monkeypatch.setattr(
        "app.v1.api.deps.AuthService.resolve_supabase_user",
        fake_resolve,
    )

    user = await get_current_user(
        request=_request_with_headers({"Authorization": "Bearer token-123"}),
    )

    assert user.id == "user-1"
    assert user.username == "alice@example.com"


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_bearer_token_for_supabase(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await get_current_user(
            request=_request_with_headers({}),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_resolve_supabase_user_uses_certifi_bundle_for_api_fallback(monkeypatch):
    captured = {}

    async def fake_local_verify(_token: str):
        return None

    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "id": "user-1",
                "email": "alice@example.com",
                "user_metadata": {},
                "app_metadata": {},
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            captured["verify"] = kwargs.get("verify")
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return DummyResponse()

    monkeypatch.setattr(
        "app.v1.services.auth_service.settings",
        SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="publishable-key",
            supabase_secret_key="",
        ),
    )
    monkeypatch.setattr(
        "app.v1.services.auth_service.AuthService._resolve_supabase_user_locally",
        staticmethod(fake_local_verify),
    )
    monkeypatch.setattr("app.v1.services.auth_service.httpx.AsyncClient", DummyClient)

    user = await AuthService.resolve_supabase_user("token-123")

    assert user.id == "user-1"
    assert captured["url"] == "https://example.supabase.co/auth/v1/user"
    assert captured["headers"]["Authorization"] == "Bearer token-123"
    assert captured["headers"]["apikey"] == "publishable-key"
    assert str(captured["verify"]).endswith("cacert.pem")


@pytest.mark.asyncio
async def test_resolve_supabase_user_logs_through_app_logger(monkeypatch):
    captured_messages = []

    async def fake_local_verify(_token: str):
        return None

    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "id": "user-1",
                "email": "alice@example.com",
                "user_metadata": {},
                "app_metadata": {},
            }

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers):
            return DummyResponse()

    monkeypatch.setattr(
        "app.v1.services.auth_service.settings",
        SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="publishable-key",
            supabase_secret_key="",
        ),
    )
    monkeypatch.setattr(
        "app.v1.services.auth_service.AuthService._resolve_supabase_user_locally",
        staticmethod(fake_local_verify),
    )
    monkeypatch.setattr("app.v1.services.auth_service.httpx.AsyncClient", DummyClient)
    monkeypatch.setattr(
        "app.v1.services.auth_service.logprint",
        lambda *args, **kwargs: captured_messages.append((args, kwargs)),
    )

    await AuthService.resolve_supabase_user("token-123")

    messages = [" ".join(str(part) for part in args) for args, _kwargs in captured_messages]
    assert any("Starting Supabase /auth/v1/user verification" in message for message in messages)
    assert any("COMPLETED with 200 in" in message for message in messages)


@pytest.mark.asyncio
async def test_resolve_supabase_user_verifies_jwt_locally_without_network(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(public_key)
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "alice@example.com",
            "app_metadata": {"plan": "pro"},
            "iss": "https://example.supabase.co/auth/v1",
            "exp": 4102444800,
        },
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        algorithm="RS256",
        headers={"kid": "kid-1"},
    )

    monkeypatch.setattr(
        "app.v1.services.auth_service.settings",
        SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="publishable-key",
            supabase_secret_key="",
        ),
    )
    async def fake_get_cached_jwks(force_refresh: bool = False):
        _ = force_refresh
        return [{"kid": "kid-1", "alg": "RS256", **json.loads(public_jwk)}]

    monkeypatch.setattr(
        "app.v1.services.auth_service.AuthService._get_cached_jwks",
        staticmethod(fake_get_cached_jwks),
    )

    class FailingClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("network fallback should not run for locally verifiable JWTs")

    monkeypatch.setattr("app.v1.services.auth_service.httpx.AsyncClient", FailingClient)

    user = await AuthService.resolve_supabase_user(token)

    assert user.id == "user-1"
    assert user.username == "alice@example.com"
    assert user.plan == "PRO"


@pytest.mark.asyncio
async def test_v1_settings_reads_public_supabase_config_from_inquira_toml(tmp_path, monkeypatch):
    config_path = tmp_path / "inquira.toml"
    config_path.write_text(
        """
[auth.supabase]
url = "https://public.example.supabase.co"
publishable_key = "sb_publishable_test"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.delenv("INQUIRA_SUPABASE_URL", raising=False)
    monkeypatch.delenv("SB_INQUIRA_CE_URL", raising=False)
    monkeypatch.delenv("INQUIRA_SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SB_INQUIRA_CE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("INQUIRA_TOML_PATH", str(config_path))

    settings = V1Settings.load()

    assert settings.supabase_url == "https://public.example.supabase.co"
    assert settings.supabase_publishable_key == "sb_publishable_test"
