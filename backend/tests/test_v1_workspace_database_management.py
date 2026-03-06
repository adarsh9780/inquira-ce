from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.services.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_rename_workspace_updates_name_and_manifest(monkeypatch):
    workspace = SimpleNamespace(
        id="ws-1",
        name="Old Name",
        name_normalized="old name",
        is_active=1,
        duckdb_path="/tmp/ws-1/workspace.db",
        created_at=datetime(2026, 3, 1, 10, 0, 0),
        updated_at=datetime(2026, 3, 1, 10, 1, 0),
    )
    user = SimpleNamespace(id="user-1", username="alice")
    calls = {}

    async def fake_get_by_id(_session, workspace_id, principal_id):
        calls["lookup"] = (workspace_id, principal_id)
        return workspace

    async def fake_get_by_name_normalized(_session, _principal_id, _name_normalized):
        return None

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

    monkeypatch.setattr("app.v1.services.workspace_service.WorkspaceRepository.get_by_id", fake_get_by_id)
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_name_normalized",
        fake_get_by_name_normalized,
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

    renamed = await WorkspaceService.rename_workspace(
        session=DummySession(),
        user=user,
        workspace_id="ws-1",
        name="  New Workspace Name  ",
    )

    assert renamed is workspace
    assert workspace.name == "New Workspace Name"
    assert workspace.name_normalized == "new workspace name"
    assert calls["lookup"] == ("ws-1", "user-1")
    assert calls["manifest"][0] == "alice"
    assert calls["manifest"][2] == "New Workspace Name"


@pytest.mark.asyncio
async def test_clear_workspace_database_removes_workspace_db_and_scratchpad(monkeypatch, tmp_path):
    workspace_dir = tmp_path / ".inquira" / "alice" / "workspaces" / "ws-1"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_db = workspace_dir / "workspace.db"
    workspace_db.write_text("db", encoding="utf-8")
    scratchpad_db = workspace_dir / "scratchpad" / "artifacts.duckdb"
    scratchpad_db.parent.mkdir(parents=True, exist_ok=True)
    scratchpad_db.write_text("scratch", encoding="utf-8")
    schema_path = workspace_dir / "meta" / "table_schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text("{}", encoding="utf-8")

    workspace = SimpleNamespace(id="ws-1", duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="user-1", username="alice")
    calls = {"deleted": False, "committed": False}

    async def fake_get_by_id(_session, workspace_id, principal_id):
        assert workspace_id == "ws-1"
        assert principal_id == "user-1"
        return workspace

    async def fake_list_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-1"
        return [SimpleNamespace(schema_path=str(schema_path))]

    async def fake_delete_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-1"
        calls["deleted"] = True

    async def fake_stop_terminal_session(*, user_id, workspace_id):
        assert user_id == "user-1"
        assert workspace_id == "ws-1"
        return True

    async def fake_reset_workspace_kernel(_workspace_id):
        assert _workspace_id == "ws-1"
        return True

    monkeypatch.setattr("app.v1.services.workspace_service.WorkspaceRepository.get_by_id", fake_get_by_id)
    monkeypatch.setattr("app.v1.services.workspace_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.workspace_service.DatasetRepository.delete_for_workspace", fake_delete_for_workspace)
    monkeypatch.setattr("app.v1.services.workspace_service.stop_workspace_terminal_session", fake_stop_terminal_session)
    monkeypatch.setattr("app.v1.services.workspace_service.reset_workspace_kernel", fake_reset_workspace_kernel)

    class DummySession:
        async def commit(self):
            calls["committed"] = True
            return None

    cleared, detail = await WorkspaceService.clear_workspace_database(
        session=DummySession(),
        user=user,
        workspace_id="ws-1",
    )

    assert cleared is True
    assert "re-create data" in detail.lower()
    assert calls["deleted"] is True
    assert calls["committed"] is True
    assert workspace_db.exists() is False
    assert scratchpad_db.parent.exists() is False
    assert schema_path.exists() is False


@pytest.mark.asyncio
async def test_clear_workspace_database_keeps_metadata_when_file_clear_fails(monkeypatch, tmp_path):
    workspace_dir = tmp_path / ".inquira" / "alice" / "workspaces" / "ws-2"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    workspace_db = workspace_dir / "workspace.db"
    workspace_db.write_text("db", encoding="utf-8")

    workspace = SimpleNamespace(id="ws-2", duckdb_path=str(workspace_db))
    user = SimpleNamespace(id="user-1", username="alice")
    calls = {"deleted": False, "committed": False}

    async def fake_get_by_id(_session, workspace_id, principal_id):
        assert workspace_id == "ws-2"
        assert principal_id == "user-1"
        return workspace

    async def fake_list_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-2"
        return []

    async def fake_delete_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-2"
        calls["deleted"] = True

    async def fake_stop_terminal_session(*, user_id, workspace_id):
        assert user_id == "user-1"
        assert workspace_id == "ws-2"
        return True

    async def fake_reset_workspace_kernel(_workspace_id):
        assert _workspace_id == "ws-2"
        return True

    original_unlink = Path.unlink

    def fail_workspace_unlink(path_obj, *args, **kwargs):
        if path_obj == workspace_db:
            raise OSError("database is locked")
        return original_unlink(path_obj, *args, **kwargs)

    monkeypatch.setattr("app.v1.services.workspace_service.WorkspaceRepository.get_by_id", fake_get_by_id)
    monkeypatch.setattr("app.v1.services.workspace_service.DatasetRepository.list_for_workspace", fake_list_for_workspace)
    monkeypatch.setattr("app.v1.services.workspace_service.DatasetRepository.delete_for_workspace", fake_delete_for_workspace)
    monkeypatch.setattr("app.v1.services.workspace_service.stop_workspace_terminal_session", fake_stop_terminal_session)
    monkeypatch.setattr("app.v1.services.workspace_service.reset_workspace_kernel", fake_reset_workspace_kernel)
    monkeypatch.setattr(Path, "unlink", fail_workspace_unlink)

    class DummySession:
        async def commit(self):
            calls["committed"] = True
            return None

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.clear_workspace_database(
            session=DummySession(),
            user=user,
            workspace_id="ws-2",
        )

    assert exc.value.status_code == 409
    assert "could not clear workspace database" in str(exc.value.detail).lower()
    assert calls["deleted"] is False
    assert calls["committed"] is False
    assert workspace_db.exists() is True
