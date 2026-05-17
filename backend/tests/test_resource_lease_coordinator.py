from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.data_access.coordinator import LeaseConflictError, LeaseKinds, ResourceLeaseCoordinator
from app.v1 import models  # noqa: F401
from app.v1.db.base import AppDataBase


@pytest.fixture
async def lease_session(tmp_path):
    db_path = tmp_path / "leases.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(AppDataBase.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_resource_lease_coordinator_acquire_and_release(lease_session) -> None:
    coordinator = ResourceLeaseCoordinator(lease_seconds=30)

    lease = await coordinator.acquire_workspace_runtime_lease(
        lease_session,
        workspace_id="workspace-1",
        owner_token="owner-1",
        metadata={"source": "test"},
    )
    await lease_session.commit()

    assert lease.resource_key == "workspace-1"
    assert lease.lease_kind == LeaseKinds.WORKSPACE_RUNTIME

    await coordinator.release_lease(
        lease_session,
        resource_key="workspace-1",
        lease_kind=LeaseKinds.WORKSPACE_RUNTIME,
        owner_token="owner-1",
    )
    await lease_session.commit()

    await coordinator.release_lease(
        lease_session,
        resource_key="workspace-1",
        lease_kind=LeaseKinds.WORKSPACE_RUNTIME,
        owner_token="owner-1",
    )
    await lease_session.commit()


@pytest.mark.asyncio
async def test_resource_lease_coordinator_rejects_conflicting_workspace_leases(lease_session) -> None:
    coordinator = ResourceLeaseCoordinator(lease_seconds=30)
    await coordinator.acquire_workspace_runtime_lease(
        lease_session,
        workspace_id="workspace-1",
        owner_token="runtime-owner",
    )
    await lease_session.commit()

    with pytest.raises(LeaseConflictError, match="Conflicting active lease"):
        await coordinator.acquire_workspace_maintenance_lease(
            lease_session,
            workspace_id="workspace-1",
            owner_token="maintenance-owner",
        )


@pytest.mark.asyncio
async def test_resource_lease_coordinator_reclaims_expired_lease(lease_session) -> None:
    coordinator = ResourceLeaseCoordinator(lease_seconds=30)
    lease = await coordinator.acquire_workspace_runtime_lease(
        lease_session,
        workspace_id="workspace-1",
        owner_token="owner-1",
    )
    lease.leased_until = datetime.now(UTC) - timedelta(seconds=1)
    await lease_session.commit()

    renewed = await coordinator.acquire_workspace_runtime_lease(
        lease_session,
        workspace_id="workspace-1",
        owner_token="owner-2",
    )
    await lease_session.commit()

    assert renewed.owner_token == "owner-2"
    assert renewed.leased_until > datetime.now(UTC)


@pytest.mark.asyncio
async def test_resource_lease_coordinator_renews_owned_lease(lease_session) -> None:
    coordinator = ResourceLeaseCoordinator(lease_seconds=30)
    lease = await coordinator.acquire_principal_activation_lease(
        lease_session,
        principal_id="principal-1",
        owner_token="owner-1",
        metadata={"step": 1},
    )
    await lease_session.commit()
    original_expiry = lease.leased_until

    renewed = await coordinator.renew_lease(
        lease_session,
        resource_key="principal-1",
        lease_kind=LeaseKinds.PRINCIPAL_ACTIVATION,
        owner_token="owner-1",
        metadata={"step": 2},
    )
    await lease_session.commit()

    assert renewed.leased_until >= original_expiry
    assert renewed.metadata_json == '{"step": 2}'


@pytest.mark.asyncio
async def test_resource_lease_coordinator_runtime_and_maintenance_are_mutually_exclusive(lease_session) -> None:
    coordinator = ResourceLeaseCoordinator(lease_seconds=30)
    await coordinator.acquire_workspace_maintenance_lease(
        lease_session,
        workspace_id="workspace-1",
        owner_token="maintenance-owner",
    )
    await lease_session.commit()

    with pytest.raises(LeaseConflictError, match="Conflicting active lease"):
        await coordinator.assert_no_conflicting_lease(
            lease_session,
            resource_key="workspace-1",
            resource_type="workspace",
            conflicting_kinds=(LeaseKinds.WORKSPACE_MAINTENANCE,),
            owner_token="runtime-owner",
        )
