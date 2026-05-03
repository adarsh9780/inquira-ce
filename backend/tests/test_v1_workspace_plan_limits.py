from types import SimpleNamespace

import pytest

from app.v1.services.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_free_plan_can_create_a_second_workspace(monkeypatch):
    async def fake_get_by_name_normalized(_session, _principal_id, _normalized):
        return None

    async def fake_count_for_principal(_session, _principal_id):
        return 1

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
            id="ws-2",
            owner_principal_id=principal_id,
            name=name,
            name_normalized=name_normalized,
            duckdb_path=duckdb_path,
            is_active=is_active,
            created_at="2026-03-31T10:00:00",
            updated_at="2026-03-31T10:00:00",
        )

    calls = {}

    async def fake_ensure_workspace_dirs(username, workspace_id):
        calls["ensure_dirs"] = (username, workspace_id)

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
    workspace = await WorkspaceService.create_workspace(
        session=DummySession(),
        user=user,
        name="Analytics",
    )

    assert workspace.id == "ws-2"
    assert workspace.is_active == 0
    assert calls["ensure_dirs"] == ("alice", "ws-2")
    assert calls["manifest"][0] == "alice"
    assert calls["manifest"][1] == "ws-2"
    assert calls["manifest"][2] == "Analytics"
    assert calls["manifest"][3] == "analytics"
    assert calls["schema_context"] == ""
