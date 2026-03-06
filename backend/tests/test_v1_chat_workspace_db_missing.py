from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_fails_when_workspace_db_missing_for_managed_workspace(monkeypatch, tmp_path):
    missing_db = tmp_path / ".inquira" / "alice" / "workspaces" / "ws-1" / "workspace.db"

    async def fake_get_workspace(_session, _workspace_id, _user_id):
        return SimpleNamespace(id="ws-1", duckdb_path=str(missing_db))

    monkeypatch.setattr("app.v1.services.chat_service.WorkspaceRepository.get_by_id", fake_get_workspace)

    session = SimpleNamespace()
    user = SimpleNamespace(id="u1", username="alice")
    langgraph_manager = SimpleNamespace(get_graph=None)

    with pytest.raises(HTTPException) as exc:
        await ChatService.analyze_and_persist_turn(
            session=session,
            langgraph_manager=langgraph_manager,
            user=user,
            workspace_id="ws-1",
            conversation_id=None,
            question="hello",
            current_code="",
            model="gemini-2.5-flash",
            context=None,
            api_key="x",
        )

    assert exc.value.status_code == 409
    assert "workspace database is missing" in str(exc.value.detail).lower()
    assert "re-create" in str(exc.value.detail).lower()
