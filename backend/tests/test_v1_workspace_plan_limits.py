from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.services.workspace_service import WorkspaceService


@pytest.mark.asyncio
async def test_free_plan_workspace_limit_error_is_descriptive(monkeypatch):
    async def fake_get_by_name_normalized(_session, _user_id, _normalized):
        return None

    async def fake_count_for_user(_session, _user_id):
        return 1

    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.get_by_name_normalized",
        fake_get_by_name_normalized,
    )
    monkeypatch.setattr(
        "app.v1.services.workspace_service.WorkspaceRepository.count_for_user",
        fake_count_for_user,
    )

    user = SimpleNamespace(id="user-1", username="alice", plan=SimpleNamespace(value="FREE"))

    with pytest.raises(HTTPException) as exc:
        await WorkspaceService.create_workspace(session=object(), user=user, name="Analytics")

    assert exc.value.status_code == 403
    assert "Free plan" in exc.value.detail
    assert "1 workspace" in exc.value.detail
