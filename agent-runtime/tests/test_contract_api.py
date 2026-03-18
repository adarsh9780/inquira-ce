from fastapi.testclient import TestClient

from runtime_server.service import create_app


def test_health_exposes_api_major():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert int(body["api_major"]) >= 1
    assert str(body.get("active_agent") or "").strip() != ""


def test_run_requires_bearer_auth_when_shared_secret_unset():
    app = create_app()
    client = TestClient(app)
    resp = client.post("/v1/agent/run", json={})
    assert resp.status_code in {401, 422, 503}
