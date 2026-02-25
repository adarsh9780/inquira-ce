from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_v1_login_session_is_used_consistently_across_endpoints():
    username = f"user_{uuid4().hex[:10]}"
    password = "secret123"

    with TestClient(app) as client:
        register = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        assert register.status_code == 200
        registered_user_id = register.json()["user_id"]

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user_id"] == registered_user_id

        workspaces = client.get("/api/v1/workspaces")
        assert workspaces.status_code == 200

        created = client.post("/api/v1/workspaces", json={"name": "Session Check"})
        assert created.status_code == 200

        listed = client.get("/api/v1/workspaces")
        assert listed.status_code == 200
        items = listed.json().get("workspaces", [])
        assert any(item.get("name") == "Session Check" for item in items)
