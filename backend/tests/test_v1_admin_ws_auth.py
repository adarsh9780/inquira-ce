from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.v1.api import admin as admin_api
from app.v1.api import deps as v1_deps


def test_admin_test_gemini_requires_auth_cookie():
    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/test-gemini",
        json={"api_key": "test-key", "model": "google/gemini-2.5-flash"},
    )
    assert response.status_code == 401


def test_admin_test_gemini_allows_authenticated_user(monkeypatch):
    def _fake_current_user():
        return SimpleNamespace(id="user-1")

    def _fake_ask(self, user_query, structured_output_format, max_tokens=None):  # noqa: ARG001
        return "OK"

    app.dependency_overrides[v1_deps.get_current_user] = _fake_current_user
    monkeypatch.setattr(admin_api.LLMService, "ask", _fake_ask)
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/admin/test-gemini",
            json={"api_key": "test-key", "model": "google/gemini-2.5-flash"},
        )
        assert response.status_code == 200
        assert response.json().get("detail") == "API key is valid and working correctly"
    finally:
        app.dependency_overrides.pop(v1_deps.get_current_user, None)


def test_ws_settings_rejects_unauthenticated_client(monkeypatch):
    async def _fake_resolve_user(_websocket):
        return None

    monkeypatch.setattr("app.main._resolve_websocket_user", _fake_resolve_user)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/settings/user-1"):
            pass
    assert exc_info.value.code == 1008


def test_ws_settings_rejects_user_mismatch(monkeypatch):
    async def _fake_resolve_user(_websocket):
        return SimpleNamespace(id="user-1")

    monkeypatch.setattr("app.main._resolve_websocket_user", _fake_resolve_user)
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/settings/user-2"):
            pass
    assert exc_info.value.code == 1008


def test_ws_settings_accepts_authenticated_matching_user(monkeypatch):
    async def _fake_resolve_user(_websocket):
        return SimpleNamespace(id="user-1")

    monkeypatch.setattr("app.main._resolve_websocket_user", _fake_resolve_user)
    client = TestClient(app)
    with client.websocket_connect("/ws/settings/user-1") as websocket:
        payload = websocket.receive_json()
        assert payload.get("type") == "connected"
