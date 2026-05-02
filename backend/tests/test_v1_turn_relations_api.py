from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.v1.api.deps import ensure_appdata_principal, get_current_user
from app.v1.db.session import get_appdata_db_session


def test_turn_relations_api_returns_parent_children_and_neighbors(monkeypatch):
    async def fake_relations(*, session, principal_id, conversation_id, turn_id):
        _ = session, principal_id, conversation_id, turn_id
        return {
            "current": {
                "id": "turn-2",
                "parent_turn_id": "turn-1",
                "result_kind": "figure",
                "code_path": "/tmp/turn-2/analysis.py",
                "manifest_path": "/tmp/turn-2/turn.json",
                "seq_no": 2,
                "user_text": "branch question",
                "assistant_text": "branch answer",
                "tool_events": None,
                "metadata": None,
                "code_snapshot": "print('2')",
                "created_at": "2026-05-02T10:00:00Z",
            },
            "parent": {
                "id": "turn-1",
                "parent_turn_id": None,
                "result_kind": "dataframe",
                "code_path": None,
                "manifest_path": None,
                "seq_no": 1,
                "user_text": "root question",
                "assistant_text": "root answer",
                "tool_events": None,
                "metadata": None,
                "code_snapshot": "print('1')",
                "created_at": "2026-05-02T09:00:00Z",
            },
            "children": [
                {
                    "id": "turn-3",
                    "parent_turn_id": "turn-2",
                    "result_kind": "dataframe",
                    "code_path": None,
                    "manifest_path": None,
                    "seq_no": 3,
                    "user_text": "next question",
                    "assistant_text": "next answer",
                    "tool_events": None,
                    "metadata": None,
                    "code_snapshot": "print('3')",
                    "created_at": "2026-05-02T11:00:00Z",
                }
            ],
            "previous_turn": {
                "id": "turn-1",
                "parent_turn_id": None,
                "result_kind": "dataframe",
                "code_path": None,
                "manifest_path": None,
                "seq_no": 1,
                "user_text": "root question",
                "assistant_text": "root answer",
                "tool_events": None,
                "metadata": None,
                "code_snapshot": "print('1')",
                "created_at": "2026-05-02T09:00:00Z",
            },
            "next_turn": {
                "id": "turn-3",
                "parent_turn_id": "turn-2",
                "result_kind": "dataframe",
                "code_path": None,
                "manifest_path": None,
                "seq_no": 3,
                "user_text": "next question",
                "assistant_text": "next answer",
                "tool_events": None,
                "metadata": None,
                "code_snapshot": "print('3')",
                "created_at": "2026-05-02T11:00:00Z",
            },
            "final_turn": None,
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
    monkeypatch.setattr("app.v1.api.conversations.ConversationService.get_turn_relations", fake_relations)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/conversations/conv-1/turns/turn-2/relations")
        assert response.status_code == 200
        payload = response.json()
        assert payload["current"]["id"] == "turn-2"
        assert payload["parent"]["id"] == "turn-1"
        assert payload["children"][0]["id"] == "turn-3"
        assert payload["previous_turn"]["id"] == "turn-1"
        assert payload["next_turn"]["id"] == "turn-3"
    finally:
        app.dependency_overrides.clear()
