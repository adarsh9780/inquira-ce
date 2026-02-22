"""Contract checks for required API v1 routes and payload shapes."""

from app.main import app


def test_openapi_contains_required_v1_routes():
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/workspaces" in paths
    assert "/api/v1/chat/analyze" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/browser-sync" in paths
    assert "/api/v1/preferences" in paths
    assert "/api/v1/preferences/api-key" in paths


def test_v1_analyze_contract_includes_workspace_dataset_fields():
    schema = app.openapi()
    analyze = schema["paths"]["/api/v1/chat/analyze"]["post"]
    request_ref = analyze["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    component_name = request_ref.split("/")[-1]
    request_schema = schema["components"]["schemas"][component_name]
    properties = request_schema["properties"]

    assert "workspace_id" in properties
    assert "conversation_id" in properties
    assert "table_name" in properties
    assert "active_schema" in properties
    assert "api_key" in properties
