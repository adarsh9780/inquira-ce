"""Authentication service for Supabase-backed identity."""

from __future__ import annotations

import certifi
import httpx
import jwt
import time
from typing import Any
from fastapi import HTTPException

from ...core.logger import logprint
from ..core.settings import settings
from ..repositories.auth_repository import AuthUserRecord

_JWKS_CACHE_TTL_SECONDS = 300
_jwks_cache: dict[str, Any] = {
    "issuer": "",
    "expires_at": 0.0,
    "keys": [],
}


def _supabase_auth_issuer(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/auth/v1"


def _auth_user_from_payload(payload: dict[str, Any]) -> AuthUserRecord:
    metadata = payload.get("user_metadata") or {}
    app_metadata = payload.get("app_metadata") or {}
    user_id = str(payload.get("sub") or payload.get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Supabase user payload missing id")

    username = (
        str(payload.get("email") or "").strip()
        or str(payload.get("phone") or "").strip()
        or str(payload.get("preferred_username") or "").strip()
        or str(metadata.get("full_name") or "").strip()
        or str(metadata.get("name") or "").strip()
        or user_id
    )
    plan = str(app_metadata.get("plan") or payload.get("plan") or "FREE").strip() or "FREE"

    return AuthUserRecord(
        id=user_id,
        username=username,
        password_hash="",
        salt="",
        plan=plan.upper(),
    )


class AuthService:
    """Business logic for validating Supabase access tokens."""

    @staticmethod
    def _fallback_api_key() -> str:
        return (
            str(settings.supabase_publishable_key or "").strip()
            or str(settings.supabase_secret_key or "").strip()
        )

    @staticmethod
    async def _get_cached_jwks(force_refresh: bool = False) -> list[dict[str, Any]] | None:
        issuer = _supabase_auth_issuer(settings.supabase_url)
        now = time.time()
        if (
            not force_refresh
            and _jwks_cache["issuer"] == issuer
            and now < float(_jwks_cache["expires_at"] or 0.0)
        ):
            return list(_jwks_cache["keys"] or [])

        jwks_url = f"{issuer}/.well-known/jwks.json"
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=certifi.where()) as client:
                response = await client.get(jwks_url)
        except httpx.HTTPError as exc:
            logprint(
                f"[AUTH PROFILE] Failed to fetch Supabase JWKS from {jwks_url}: {exc}",
                level="warning",
            )
            return None

        if response.status_code >= 400:
            logprint(
                f"[AUTH PROFILE] Supabase JWKS fetch returned {response.status_code} from {jwks_url}",
                level="warning",
            )
            return None

        payload = response.json()
        keys = payload.get("keys")
        if not isinstance(keys, list) or not keys:
            logprint(
                f"[AUTH PROFILE] Supabase JWKS payload from {jwks_url} did not contain usable signing keys",
                level="warning",
            )
            return None

        _jwks_cache["issuer"] = issuer
        _jwks_cache["expires_at"] = now + _JWKS_CACHE_TTL_SECONDS
        _jwks_cache["keys"] = list(keys)
        return list(keys)

    @staticmethod
    def _select_jwk_key(
        keys: list[dict[str, Any]],
        kid: str,
        algorithm: str,
    ) -> Any | None:
        for key in keys:
            if str(key.get("kid") or "").strip() != kid:
                continue
            key_alg = str(key.get("alg") or "").strip().upper()
            if key_alg and key_alg != algorithm:
                continue
            return jwt.PyJWK.from_dict(key).key
        return None

    @staticmethod
    async def _resolve_supabase_user_locally(access_token: str) -> AuthUserRecord | None:
        if not settings.supabase_url:
            return None

        try:
            header = jwt.get_unverified_header(access_token)
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token") from exc

        algorithm = str(header.get("alg") or "").strip().upper()
        if not algorithm or algorithm == "NONE":
            raise HTTPException(status_code=401, detail="Invalid bearer token")

        signing_key = None
        if algorithm.startswith("HS"):
            secret = str(settings.supabase_secret_key or "").strip()
            if not secret:
                return None
            signing_key = secret
        else:
            kid = str(header.get("kid") or "").strip()
            if not kid:
                return None
            keys = await AuthService._get_cached_jwks(force_refresh=False)
            if not keys:
                return None
            signing_key = AuthService._select_jwk_key(keys, kid, algorithm)
            if signing_key is None:
                keys = await AuthService._get_cached_jwks(force_refresh=True)
                if not keys:
                    return None
                signing_key = AuthService._select_jwk_key(keys, kid, algorithm)
            if signing_key is None:
                return None

        start_time = time.perf_counter()
        logprint(
            "[AUTH PROFILE] Starting local Supabase JWT verification...",
            level="INFO",
        )
        try:
            payload = jwt.decode(
                access_token,
                signing_key,
                algorithms=[algorithm],
                issuer=_supabase_auth_issuer(settings.supabase_url),
                options={
                    "verify_aud": False,
                    "require": ["sub", "exp"],
                },
            )
        except jwt.PyJWTError as exc:
            elapsed = time.perf_counter() - start_time
            logprint(
                f"[AUTH PROFILE] Local Supabase JWT verification FAILED after {elapsed:.3f}s",
                level="ERROR",
            )
            raise HTTPException(status_code=401, detail="Invalid bearer token") from exc

        elapsed = time.perf_counter() - start_time
        logprint(
            f"[AUTH PROFILE] Local Supabase JWT verification COMPLETED in {elapsed:.3f}s",
            level="INFO",
        )
        return _auth_user_from_payload(payload)

    @staticmethod
    async def _resolve_supabase_user_via_api(access_token: str) -> AuthUserRecord:
        api_key = AuthService._fallback_api_key()
        if not settings.supabase_url or not api_key:
            raise HTTPException(
                status_code=500,
                detail="Supabase auth verification is not configured on the backend.",
            )

        url = f"{_supabase_auth_issuer(settings.supabase_url)}/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": api_key,
        }

        start_time = time.perf_counter()
        logprint(
            "[AUTH PROFILE] Starting Supabase /auth/v1/user verification...",
            level="INFO",
        )

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=certifi.where()) as client:
                response = await client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            elapsed = time.perf_counter() - start_time
            logprint(
                f"[AUTH PROFILE] Supabase /auth/v1/user verification EXCEPTION Timeout after {elapsed:.3f}s",
                level="ERROR",
            )
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup timed out. Check network or TLS configuration.",
            ) from exc
        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - start_time
            logprint(
                f"[AUTH PROFILE] Supabase /auth/v1/user verification EXCEPTION HTTPError after {elapsed:.3f}s",
                level="ERROR",
            )
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            ) from exc

        elapsed_time = time.perf_counter() - start_time
        logprint(
            f"[AUTH PROFILE] Supabase /auth/v1/user verification COMPLETED with {response.status_code} in {elapsed_time:.3f}s",
            level="INFO",
        )

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        if response.status_code >= 400:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            )

        return _auth_user_from_payload(response.json())

    @staticmethod
    async def resolve_supabase_user(access_token: str) -> AuthUserRecord:
        """Resolve a user profile from a Supabase bearer token."""
        token = str(access_token or "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing bearer token")

        local_user = await AuthService._resolve_supabase_user_locally(token)
        if local_user is not None:
            return local_user

        return await AuthService._resolve_supabase_user_via_api(token)
