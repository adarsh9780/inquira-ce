from fastapi.testclient import TestClient

from app.main import app


def test_v1_legal_terms_returns_markdown_payload():
    client = TestClient(app)
    response = client.get("/api/v1/legal/terms")
    assert response.status_code == 200
    payload = response.json()
    assert "markdown" in payload
    assert "Inquira Terms & Conditions" in str(payload["markdown"])
    assert "last_updated" in payload
