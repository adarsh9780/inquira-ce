from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.services.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_workspace_summary_returns_table_and_conversation_metadata(monkeypatch):
    workspace = SimpleNamespace(
        id="ws-9",
        name="Operations",
        is_active=1,
        created_at=datetime(2026, 3, 30, 9, 0, 0),
        updated_at=datetime(2026, 3, 31, 11, 30, 0),
    )

    async def fake_get_by_id(_session, workspace_id, principal_id):
        assert workspace_id == "ws-9"
        assert principal_id == "user-1"
        return workspace

    async def fake_list_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-9"
        return [
            SimpleNamespace(table_name="sales"),
            SimpleNamespace(table_name="customers"),
        ]

    async def fake_count_for_workspace(_session, workspace_id):
        assert workspace_id == "ws-9"
        return 3

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_id",
        fake_get_by_id,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.DatasetRepository.list_for_workspace",
        fake_list_for_workspace,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.ConversationRepository.count_for_workspace",
        fake_count_for_workspace,
    )

    user = SimpleNamespace(id="user-1", username="alice")
    summary = await WorkspaceService.get_workspace_summary(
        session=object(),
        user=user,
        workspace_id="ws-9",
    )

    assert summary["id"] == "ws-9"
    assert summary["name"] == "Operations"
    assert summary["is_active"] is True
    assert summary["table_count"] == 2
    assert summary["table_names"] == ["sales", "customers"]
    assert summary["conversation_count"] == 3


@pytest.mark.asyncio
async def test_workspace_summary_raises_for_missing_workspace(monkeypatch):
    async def fake_get_by_id(_session, _workspace_id, _principal_id):
        return None

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_id",
        fake_get_by_id,
    )

    user = SimpleNamespace(id="user-1", username="alice")

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.get_workspace_summary(
            session=object(),
            user=user,
            workspace_id="ws-missing",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Workspace not found"
