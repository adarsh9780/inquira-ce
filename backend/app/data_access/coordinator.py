"""Durable resource lease coordinator backed by appdata SQLite."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.models import ResourceLease


DEFAULT_LEASE_SECONDS = 60
DEFAULT_LOCK_RETRY_ATTEMPTS = 5
DEFAULT_LOCK_RETRY_BASE_DELAY_SECONDS = 0.05

T = TypeVar("T")


class LeaseConflictError(RuntimeError):
    """Raised when a conflicting active lease already exists."""


@dataclass(frozen=True)
class LeaseKinds:
    """Known durable lease kinds."""

    WORKSPACE_RUNTIME: str = "workspace_runtime"
    WORKSPACE_MAINTENANCE: str = "workspace_maintenance"
    PRINCIPAL_ACTIVATION: str = "principal_activation"
    STORAGE_CLEANUP: str = "storage_cleanup"


class ResourceLeaseCoordinator:
    """Coordinate durable claims for workspace and principal resources."""

    def __init__(
        self,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        lock_retry_attempts: int = DEFAULT_LOCK_RETRY_ATTEMPTS,
        lock_retry_base_delay_seconds: float = DEFAULT_LOCK_RETRY_BASE_DELAY_SECONDS,
    ) -> None:
        self._lease_delta = timedelta(seconds=max(5, int(lease_seconds)))
        self._lock_retry_attempts = max(1, int(lock_retry_attempts))
        self._lock_retry_base_delay_seconds = max(0.0, float(lock_retry_base_delay_seconds))

    async def acquire_workspace_runtime_lease(
        self,
        session: AsyncSession,
        *,
        workspace_id: str,
        owner_token: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceLease:
        return await self._with_sqlite_lock_retry(
            session,
            lambda: self._acquire_lease(
                session,
                resource_key=workspace_id,
                resource_type="workspace",
                lease_kind=LeaseKinds.WORKSPACE_RUNTIME,
                owner_token=owner_token,
                metadata=metadata,
                conflicting_kinds=(LeaseKinds.WORKSPACE_MAINTENANCE,),
            ),
        )

    async def acquire_workspace_maintenance_lease(
        self,
        session: AsyncSession,
        *,
        workspace_id: str,
        owner_token: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceLease:
        return await self._with_sqlite_lock_retry(
            session,
            lambda: self._acquire_lease(
                session,
                resource_key=workspace_id,
                resource_type="workspace",
                lease_kind=LeaseKinds.WORKSPACE_MAINTENANCE,
                owner_token=owner_token,
                metadata=metadata,
                conflicting_kinds=(LeaseKinds.WORKSPACE_RUNTIME,),
            ),
        )

    async def acquire_principal_activation_lease(
        self,
        session: AsyncSession,
        *,
        principal_id: str,
        owner_token: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceLease:
        return await self._with_sqlite_lock_retry(
            session,
            lambda: self._acquire_lease(
                session,
                resource_key=principal_id,
                resource_type="principal",
                lease_kind=LeaseKinds.PRINCIPAL_ACTIVATION,
                owner_token=owner_token,
                metadata=metadata,
                conflicting_kinds=(),
            ),
        )

    async def acquire_system_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceLease:
        return await self._with_sqlite_lock_retry(
            session,
            lambda: self._acquire_lease(
                session,
                resource_key=resource_key,
                resource_type="system",
                lease_kind=lease_kind,
                owner_token=owner_token,
                metadata=metadata,
                conflicting_kinds=(lease_kind,),
            ),
        )

    async def renew_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceLease:
        return await self._with_sqlite_lock_retry(
            session,
            lambda: self._renew_lease_once(
                session,
                resource_key=resource_key,
                lease_kind=lease_kind,
                owner_token=owner_token,
                metadata=metadata,
            ),
        )

    async def release_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str | None = None,
    ) -> None:
        await self._with_sqlite_lock_retry(
            session,
            lambda: self._release_lease_once(
                session,
                resource_key=resource_key,
                lease_kind=lease_kind,
                owner_token=owner_token,
            ),
        )

    async def assert_no_conflicting_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        resource_type: str,
        conflicting_kinds: tuple[str, ...],
        owner_token: str | None = None,
    ) -> None:
        if not conflicting_kinds:
            return
        now = datetime.now(UTC)
        stmt = select(ResourceLease).where(
            ResourceLease.resource_key == resource_key,
            ResourceLease.resource_type == resource_type,
            ResourceLease.lease_kind.in_(conflicting_kinds),
            ResourceLease.leased_until > now,
        )
        if owner_token is not None:
            stmt = stmt.where(ResourceLease.owner_token != owner_token)
        result = await session.execute(stmt.limit(1))
        conflict = result.scalar_one_or_none()
        if conflict is not None:
            raise LeaseConflictError(
                f"Conflicting active lease {conflict.lease_kind} exists for {resource_type}:{resource_key}."
            )

    async def assert_owned_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str,
    ) -> ResourceLease:
        lease = await self._get_lease(session, resource_key=resource_key, lease_kind=lease_kind)
        if (
            lease is None
            or lease.owner_token != owner_token
            or self._normalize_dt(lease.leased_until) <= datetime.now(UTC)
        ):
            raise LeaseConflictError(
                f"Active owned lease {lease_kind} is required for {resource_key}."
            )
        return lease

    async def get_active_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        resource_type: str,
        lease_kinds: tuple[str, ...] | None = None,
    ) -> ResourceLease | None:
        stmt = select(ResourceLease).where(
            ResourceLease.resource_key == resource_key,
            ResourceLease.resource_type == resource_type,
            ResourceLease.leased_until > datetime.now(UTC),
        )
        if lease_kinds:
            stmt = stmt.where(ResourceLease.lease_kind.in_(lease_kinds))
        result = await session.execute(stmt.order_by(ResourceLease.updated_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def _acquire_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        resource_type: str,
        lease_kind: str,
        owner_token: str,
        metadata: dict[str, Any] | None,
        conflicting_kinds: tuple[str, ...],
    ) -> ResourceLease:
        await self._delete_expired_leases(session, resource_key=resource_key, resource_type=resource_type)
        await self.assert_no_conflicting_lease(
            session,
            resource_key=resource_key,
            resource_type=resource_type,
            conflicting_kinds=conflicting_kinds,
            owner_token=owner_token,
        )
        lease = await self._get_lease(session, resource_key=resource_key, lease_kind=lease_kind)
        if lease is None:
            lease = ResourceLease(
                resource_key=resource_key,
                resource_type=resource_type,
                lease_kind=lease_kind,
                owner_token=owner_token,
                leased_until=self._expires_at(),
                metadata_json=json.dumps(metadata) if metadata is not None else None,
            )
            session.add(lease)
            await session.flush()
            return lease
        if lease.owner_token != owner_token and lease.leased_until > datetime.now(UTC):
            raise LeaseConflictError(
                f"Active lease {lease_kind} already exists for {resource_type}:{resource_key}."
            )
        lease.owner_token = owner_token
        lease.leased_until = self._expires_at()
        lease.metadata_json = json.dumps(metadata) if metadata is not None else None
        await session.flush()
        return lease

    async def _renew_lease_once(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str,
        metadata: dict[str, Any] | None,
    ) -> ResourceLease:
        lease = await self._get_lease(session, resource_key=resource_key, lease_kind=lease_kind)
        if lease is None or lease.owner_token != owner_token:
            raise LeaseConflictError(f"Lease {lease_kind} for {resource_key} is not owned by {owner_token}.")
        lease.leased_until = self._expires_at()
        if metadata is not None:
            lease.metadata_json = json.dumps(metadata)
        await session.flush()
        return lease

    async def _release_lease_once(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
        owner_token: str | None,
    ) -> None:
        lease = await self._get_lease(session, resource_key=resource_key, lease_kind=lease_kind)
        if lease is None:
            return
        if owner_token is not None and lease.owner_token != owner_token:
            return
        await session.delete(lease)
        await session.flush()

    async def _with_sqlite_lock_retry(
        self,
        session: AsyncSession,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        last_exc: BaseException | None = None
        for attempt in range(self._lock_retry_attempts):
            try:
                return await operation()
            except BaseException as exc:
                if not self._is_sqlite_locked_error(exc):
                    raise
                last_exc = exc
                await self._rollback_quietly(session)
                if attempt >= self._lock_retry_attempts - 1:
                    break
                await asyncio.sleep(self._retry_delay(attempt))
        if last_exc is not None:
            raise last_exc
        return await operation()

    def _retry_delay(self, attempt: int) -> float:
        return self._lock_retry_base_delay_seconds * (2**attempt)

    @staticmethod
    def _is_sqlite_locked_error(exc: BaseException) -> bool:
        if isinstance(exc, OperationalError):
            message = f"{exc.orig!s} {exc!s}".lower()
        else:
            message = str(exc).lower()
        return "database is locked" in message or "database table is locked" in message

    @staticmethod
    async def _rollback_quietly(session: AsyncSession) -> None:
        try:
            await session.rollback()
        except Exception:
            return

    async def _delete_expired_leases(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        resource_type: str,
    ) -> None:
        await session.execute(
            delete(ResourceLease).where(
                ResourceLease.resource_key == resource_key,
                ResourceLease.resource_type == resource_type,
                ResourceLease.leased_until <= datetime.now(UTC),
            )
        )
        await session.flush()

    async def _get_lease(
        self,
        session: AsyncSession,
        *,
        resource_key: str,
        lease_kind: str,
    ) -> ResourceLease | None:
        result = await session.execute(
            select(ResourceLease).where(
                ResourceLease.resource_key == resource_key,
                ResourceLease.lease_kind == lease_kind,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    def _expires_at(self) -> datetime:
        return datetime.now(UTC) + self._lease_delta

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
