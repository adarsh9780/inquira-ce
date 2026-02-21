from types import SimpleNamespace

import pytest

from app.v1.services.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_list_user_workspaces_excludes_active_deleting_jobs(monkeypatch):
    async def fake_list_for_user(_session, _user_id):
        return [
            SimpleNamespace(id="ws-1", name="One"),
            SimpleNamespace(id="ws-2", name="Two"),
        ]

    async def fake_list_active_jobs(_session, _user_id):
        return [SimpleNamespace(workspace_id="ws-2")]

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.list_for_user",
        fake_list_for_user,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceDeletionRepository.list_active_for_user",
        fake_list_active_jobs,
    )

    workspaces = await WorkspaceService.list_user_workspaces(session=object(), user_id="user-1")
    assert [ws.id for ws in workspaces] == ["ws-1"]
