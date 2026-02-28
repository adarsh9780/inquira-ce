"""Contract checks for new v1 runtime endpoints."""

from app.main import app


def test_openapi_contains_v1_runtime_routes():
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/v1/workspaces/{workspace_id}/execute" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/status" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/interrupt" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/reset" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/restart" in paths
    assert "/api/v1/workspaces/{workspace_id}/paths" in paths
    assert "/api/v1/workspaces/{workspace_id}/artifacts/dataframes/{artifact_id}/rows" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}/preview" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}/schema" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}/schema/regenerate" in paths
