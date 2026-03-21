"""Authentication service for Supabase-backed identity."""

from __future__ import annotations

import certifi
import httpx
from fastapi import HTTPException

from ..core.settings import settings
from ..repositories.auth_repository import AuthUserRecord


class AuthService:
    """Business logic for validating Supabase access tokens."""

    @staticmethod
    async def resolve_supabase_user(access_token: str) -> AuthUserRecord:
        """Resolve a user profile from a Supabase bearer token."""
        token = str(access_token or "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Missing bearer token")

        if not settings.supabase_url or not settings.supabase_secret_key:
            raise HTTPException(
                status_code=500,
                detail="Supabase auth is not configured on the backend.",
            )

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": settings.supabase_secret_key,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=certifi.where()) as client:
                response = await client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup timed out. Check network or TLS configuration.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            ) from exc

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        if response.status_code >= 400:
            raise HTTPException(
                status_code=503,
                detail="Supabase auth lookup failed. Please retry.",
            )

        payload = response.json()
        metadata = payload.get("user_metadata") or {}
        app_metadata = payload.get("app_metadata") or {}
        user_id = str(payload.get("id") or "").strip()
        if not user_id:
            raise HTTPException(status_code=401, detail="Supabase user payload missing id")

        username = (
            str(payload.get("email") or "").strip()
            or str(payload.get("phone") or "").strip()
            or str(metadata.get("full_name") or "").strip()
            or user_id
        )
        plan = str(app_metadata.get("plan") or "FREE").strip() or "FREE"

        return AuthUserRecord(
            id=user_id,
            username=username,
            password_hash="",
            salt="",
            plan=plan.upper(),
        )
