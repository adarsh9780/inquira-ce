from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.v1.api.deps import ensure_appdata_principal, get_current_user
from app.v1.db.session import get_appdata_db_session


def test_turn_tree_api_returns_full_tree(monkeypatch):
    async def fake_turn_tree(*, session, principal_id, conversation_id, current_turn_id):
        _ = session, principal_id, conversation_id, current_turn_id
        return {
            "roots": [
                {
                    "id": "turn-1",
                    "parent_turn_id": None,
                    "seq_no": 1,
                    "user_text": "root question",
                    "assistant_text": "root answer",
                    "created_at": "2026-05-02T09:00:00Z",
                    "children": [
                        {
                            "id": "turn-2",
                            "parent_turn_id": "turn-1",
                            "seq_no": 2,
                            "user_text": "child question",
                            "assistant_text": "child answer",
                            "created_at": "2026-05-02T10:00:00Z",
                            "children": [
                                {
                                    "id": "turn-3",
                                    "parent_turn_id": "turn-2",
                                    "seq_no": 3,
                                    "user_text": "grandchild question",
                                    "assistant_text": "grandchild answer",
                                    "created_at": "2026-05-02T11:00:00Z",
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ],
            "current_turn_id": "turn-2",
            "final_turn_id": "turn-3",
        }

    async def fake_session():
        yield SimpleNamespace()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="user-1",
        username="Ada",
        email="",
        plan="FREE",
        is_authenticated=False,
        is_guest=True,
        auth_provider="local",
    )
    app.dependency_overrides[ensure_appdata_principal] = lambda: None
    app.dependency_overrides[get_appdata_db_session] = fake_session
    monkeypatch.setattr("app.v1.api.conversations.ConversationService.get_turn_tree", fake_turn_tree)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/conversations/conv-1/turn-tree", params={"current_turn_id": "turn-2"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["current_turn_id"] == "turn-2"
        assert payload["final_turn_id"] == "turn-3"
        assert payload["roots"][0]["id"] == "turn-1"
        assert payload["roots"][0]["assistant_text"] == "root answer"
        assert payload["roots"][0]["children"][0]["id"] == "turn-2"
        assert payload["roots"][0]["children"][0]["assistant_text"] == "child answer"
        assert payload["roots"][0]["children"][0]["children"][0]["id"] == "turn-3"
        assert payload["roots"][0]["children"][0]["children"][0]["assistant_text"] == "grandchild answer"
    finally:
        app.dependency_overrides.clear()


def test_workspace_turn_tree_api_returns_final_turn_per_conversation(monkeypatch):
    async def fake_workspace_turn_tree(*, session, principal_id, workspace_id):
        _ = session, principal_id, workspace_id
        return {
            "conversations": [
                {
                    "id": "conv-1",
                    "title": "Revenue analysis",
                    "last_turn_at": "2026-05-02T11:00:00Z",
                    "created_at": "2026-05-02T09:00:00Z",
                    "updated_at": "2026-05-02T11:00:00Z",
                    "final_turn_id": "turn-2",
                    "roots": [
                        {
                            "id": "turn-1",
                            "parent_turn_id": None,
                            "seq_no": 1,
                            "sibling_order": 0,
                            "user_text": "root question",
                            "assistant_text": "root answer",
                            "created_at": "2026-05-02T09:00:00Z",
                            "children": [],
                        }
                    ],
                }
            ]
        }

    async def fake_session():
        yield SimpleNamespace()

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="user-1",
        username="Ada",
        email="",
        plan="FREE",
        is_authenticated=False,
        is_guest=True,
        auth_provider="local",
    )
    app.dependency_overrides[ensure_appdata_principal] = lambda: None
    app.dependency_overrides[get_appdata_db_session] = fake_session
    monkeypatch.setattr("app.v1.api.conversations.ConversationService.get_workspace_turn_tree", fake_workspace_turn_tree)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/workspaces/workspace-1/turn-tree")
        assert response.status_code == 200
        payload = response.json()
        assert payload["conversations"][0]["id"] == "conv-1"
        assert payload["conversations"][0]["final_turn_id"] == "turn-2"
        assert payload["conversations"][0]["roots"][0]["id"] == "turn-1"
    finally:
        app.dependency_overrides.clear()
