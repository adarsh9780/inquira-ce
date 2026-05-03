from datetime import datetime
from types import SimpleNamespace

import pytest

from app.v1.services.workspace_service import WorkspaceService
from app.v1.services.workspace_storage_service import WorkspaceStorageService


@pytest.mark.asyncio
async def test_write_workspace_manifest_persists_expected_fields(monkeypatch, tmp_path):
    user_root = tmp_path / "workspaces-root"
    monkeypatch.setattr(
        WorkspaceStorageService,
        "_user_root",
        staticmethod(lambda _username: user_root),
    )

    created_at = datetime(2026, 2, 25, 10, 0, 0)
    updated_at = datetime(2026, 2, 25, 10, 5, 0)

    manifest_path = await WorkspaceStorageService.write_workspace_manifest(
        username="alice",
        workspace_id="ws-1",
        workspace_name="Data Lab",
        normalized_name="data lab",
        created_at=created_at,
        updated_at=updated_at,
    )

    assert manifest_path.exists() is True
    raw = manifest_path.read_text(encoding="utf-8")
    assert '"workspace_id": "ws-1"' in raw
    assert '"workspace_name": "Data Lab"' in raw
    assert '"normalized_name": "data lab"' in raw
    assert '"created_at": "2026-02-25T10:00:00"' in raw
    assert '"updated_at": "2026-02-25T10:05:00"' in raw


@pytest.mark.asyncio
async def test_create_workspace_writes_manifest(monkeypatch):
    async def fake_get_by_name_normalized(_session, _principal_id, _normalized):
        return None

    async def fake_count_for_principal(_session, _principal_id):
        return 0

    async def fake_create(
        *,
        session,
        principal_id,
        name,
        name_normalized,
        duckdb_path,
        is_active,
        schema_context,
    ):
        calls["schema_context"] = schema_context
        return SimpleNamespace(
            id="ws-123",
            owner_principal_id=principal_id,
            name=name,
            name_normalized=name_normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
            created_at=datetime(2026, 2, 25, 12, 0, 0),
            updated_at=datetime(2026, 2, 25, 12, 1, 0),
        )

    calls = {}

    async def fake_ensure_workspace_dirs(_username, _workspace_id):
        calls["ensure_dirs"] = (_username, _workspace_id)

    async def fake_write_manifest(
        username,
        workspace_id,
        workspace_name,
        normalized_name,
        created_at,
        updated_at,
    ):
        calls["manifest"] = (
            username,
            workspace_id,
            workspace_name,
            normalized_name,
            created_at,
            updated_at,
        )

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_name_normalized",
        fake_get_by_name_normalized,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.count_for_principal",
        fake_count_for_principal,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.create",
        fake_create,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceStorageService.ensure_workspace_dirs",
        fake_ensure_workspace_dirs,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceStorageService.write_workspace_manifest",
        fake_write_manifest,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceStorageService.build_duckdb_path",
        staticmethod(lambda username, workspace_id: f"/tmp/{username}/{workspace_id}/workspace.duckdb"),
    )

    class DummySession:
        async def commit(self):
            return None

        async def refresh(self, _obj):
            return None

    user = SimpleNamespace(id="user-1", username="alice", plan=SimpleNamespace(value="FREE"))
    workspace = await WorkspaceService.create_workspace(session=DummySession(), user=user, name="  Data Lab  ")

    assert workspace.id == "ws-123"
    assert calls["ensure_dirs"] == ("alice", "ws-123")
    assert calls["manifest"][0] == "alice"
    assert calls["manifest"][1] == "ws-123"
    assert calls["manifest"][2] == "Data Lab"
    assert calls["manifest"][3] == "data lab"
    assert calls["schema_context"] == ""


@pytest.mark.asyncio
async def test_activate_workspace_refreshes_manifest(monkeypatch):
    previous_workspace = SimpleNamespace(id="ws-1", is_active=1)
    workspace = SimpleNamespace(
        id="ws-9",
        name="Operations",
        name_normalized="operations",
        is_active=0,
        created_at=datetime(2026, 2, 25, 13, 0, 0),
        updated_at=datetime(2026, 2, 25, 13, 5, 0),
    )
    user = SimpleNamespace(id="user-1", username="alice")
    calls = {}

    async def fake_get_by_id(_session, workspace_id, principal_id):
        calls["workspace_lookup"] = (workspace_id, principal_id)
        return workspace

    async def fake_get_active_for_principal(_session, principal_id):
        calls["previous_active_lookup"] = principal_id
        return previous_workspace

    async def fake_deactivate_all(_session, principal_id):
        calls["deactivate"] = principal_id

    async def fake_stop_terminal_session(*, user_id, workspace_id):
        calls["terminal_cleanup"] = (user_id, workspace_id)
        return True

    async def fake_reset_workspace_kernel(workspace_id):
        calls["kernel_cleanup"] = workspace_id
        return True

    async def fake_write_manifest(
        username,
        workspace_id,
        workspace_name,
        normalized_name,
        created_at,
        updated_at,
    ):
        calls["manifest"] = (
            username,
            workspace_id,
            workspace_name,
            normalized_name,
            created_at,
            updated_at,
        )

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_id",
        fake_get_by_id,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_active_for_principal",
        fake_get_active_for_principal,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.deactivate_all_for_principal",
        fake_deactivate_all,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.stop_workspace_terminal_session",
        fake_stop_terminal_session,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.reset_workspace_kernel",
        fake_reset_workspace_kernel,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceStorageService.write_workspace_manifest",
        fake_write_manifest,
    )

    class DummySession:
        async def commit(self):
            return None

        async def refresh(self, _obj):
            return None

    activated = await WorkspaceService.activate_workspace(
        session=DummySession(),
        user=user,
        workspace_id="ws-9",
    )

    assert activated is workspace
    assert workspace.is_active == 1
    assert calls["workspace_lookup"] == ("ws-9", "user-1")
    assert calls["previous_active_lookup"] == "user-1"
    assert calls["deactivate"] == "user-1"
    assert calls["terminal_cleanup"] == ("user-1", "ws-1")
    assert calls["kernel_cleanup"] == "ws-1"
    assert calls["manifest"][0] == "alice"
    assert calls["manifest"][1] == "ws-9"
