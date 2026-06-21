"""Local-only auth/session resolution for Inquira CE."""

from __future__ import annotations

from dataclasses import dataclass

from ..models.enums import UserPlan
from ..repositories.auth_repository import AuthUserRecord


DEFAULT_LOCAL_USER = AuthUserRecord(
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
    site_url: str
    manage_account_url: str
    auth_provider: str
    configured: bool


class LocalAuthService:
    @staticmethod
    def public_auth_config() -> PublicAuthConfig:
        return PublicAuthConfig(
            site_url="",
            manage_account_url="",
            auth_provider="local",
            configured=False,
        )

    @staticmethod
    def manage_account_url() -> str:
        return ""

    @staticmethod
    async def resolve_current_user(_authorization_header: str | None) -> AuthUserRecord:
        return DEFAULT_LOCAL_USER

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
        return LocalAuthService.plan_rank(plan) >= LocalAuthService.plan_rank(required)
