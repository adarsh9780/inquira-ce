"""Supabase-backed auth and entitlement resolution for CE desktop sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from ..core.settings import settings
from ..models.enums import UserPlan
from ..repositories.auth_repository import AuthUserRecord


DEFAULT_GUEST_USER = AuthUserRecord(
    id="local-user",
    username="Local User",
    email="",
    password_hash="",
    salt="",
    plan=UserPlan.FREE.value,
    is_authenticated=False,
    is_guest=True,
    auth_provider="local",
)


@dataclass(frozen=True)
class PublicAuthConfig:
    supabase_url: str
    publishable_key: str
    site_url: str
    manage_account_url: str
    auth_provider: str
    configured: bool


class SupabaseAuthService:
    @staticmethod
    def public_auth_config() -> PublicAuthConfig:
        configured = bool(settings.supabase_url and settings.supabase_publishable_key)
        return PublicAuthConfig(
            supabase_url=settings.supabase_url,
            publishable_key=settings.supabase_publishable_key,
            site_url=settings.supabase_site_url,
            manage_account_url=settings.supabase_manage_account_url,
            auth_provider=settings.auth_provider,
            configured=configured,
        )

    @staticmethod
    def manage_account_url() -> str:
        return settings.supabase_manage_account_url or settings.supabase_site_url or ""

    @staticmethod
    async def resolve_current_user(authorization_header: str | None) -> AuthUserRecord:
        token = SupabaseAuthService._extract_bearer_token(authorization_header)
        if not token:
            return DEFAULT_GUEST_USER
        if not settings.supabase_url or not settings.supabase_publishable_key:
            return DEFAULT_GUEST_USER

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                profile = await SupabaseAuthService._fetch_supabase_user(client, token)
                if not profile:
                    return DEFAULT_GUEST_USER
                plan = await SupabaseAuthService._fetch_plan_for_user(client, profile["id"])
        except Exception:
            return DEFAULT_GUEST_USER

        email = str(profile.get("email") or "").strip()
        metadata = profile.get("user_metadata") or {}
        username = (
            str(metadata.get("full_name") or "").strip()
            or str(metadata.get("name") or "").strip()
            or email
            or "Authenticated User"
        )
        provider = str(profile.get("app_metadata", {}).get("provider") or "google").strip() or "google"
        return AuthUserRecord(
            id=str(profile.get("id") or "").strip() or DEFAULT_GUEST_USER.id,
            username=username,
            email=email,
            password_hash="",
            salt="",
            plan=plan,
            is_authenticated=True,
            is_guest=False,
            auth_provider=provider,
        )

    @staticmethod
    def plan_rank(plan: str | UserPlan) -> int:
        normalized = str(plan.value if hasattr(plan, "value") else plan or UserPlan.FREE.value).upper()
        order = {
            UserPlan.FREE.value: 0,
            UserPlan.PRO.value: 1,
            UserPlan.ENTERPRISE.value: 2,
        }
        return order.get(normalized, 0)

    @staticmethod
    def has_minimum_plan(plan: str | UserPlan, required: str | UserPlan) -> bool:
        return SupabaseAuthService.plan_rank(plan) >= SupabaseAuthService.plan_rank(required)

    @staticmethod
    def _extract_bearer_token(authorization_header: str | None) -> str:
        value = str(authorization_header or "").strip()
        if not value.lower().startswith("bearer "):
            return ""
        return value.split(" ", 1)[1].strip()

    @staticmethod
    async def _fetch_supabase_user(client: httpx.AsyncClient, access_token: str) -> dict[str, Any] | None:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    @staticmethod
    async def _fetch_plan_for_user(client: httpx.AsyncClient, user_id: str) -> str:
        if not settings.supabase_secret_key:
            return UserPlan.FREE.value
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_plan_table}",
            params={
                "user_id": f"eq.{quote(user_id, safe='')}",
                "select": "plan",
                "limit": "1",
            },
            headers={
                "apikey": settings.supabase_secret_key,
                "Authorization": f"Bearer {settings.supabase_secret_key}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return UserPlan.FREE.value
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            return UserPlan.FREE.value
        candidate = str((rows[0] or {}).get("plan") or UserPlan.FREE.value).strip().upper()
        if candidate not in {UserPlan.FREE.value, UserPlan.PRO.value, UserPlan.ENTERPRISE.value}:
            return UserPlan.FREE.value
        return candidate
