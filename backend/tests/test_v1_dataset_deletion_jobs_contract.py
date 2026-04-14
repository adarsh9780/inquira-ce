"""Contract checks for async dataset deletion job APIs."""

from app.main import app


def test_openapi_contains_dataset_deletion_job_routes():
    schema = app.openapi()
    paths = schema.get("paths", {})

    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/deletions" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/deletions/{job_id}" in paths
    assert "delete" in paths["/api/v1/workspaces/{workspace_id}/datasets/{table_name}"]
    assert "get" in paths["/api/v1/workspaces/{workspace_id}/datasets/deletions"]
    assert "get" in paths["/api/v1/workspaces/{workspace_id}/datasets/deletions/{job_id}"]


def test_openapi_dataset_delete_returns_job_payload():
    schema = app.openapi()
    delete_op = schema["paths"]["/api/v1/workspaces/{workspace_id}/datasets/{table_name}"]["delete"]
    responses = delete_op.get("responses", {})

    assert "202" in responses
    body_schema = responses["202"]["content"]["application/json"]["schema"]
    assert body_schema.get("$ref", "").endswith("/DatasetDeletionJobResponse")

    components = schema.get("components", {}).get("schemas", {})
    job_response = components.get("DatasetDeletionJobResponse", {})
    job_properties = job_response.get("properties", {})
    assert "job_id" in job_properties
    assert "workspace_id" in job_properties
    assert "table_name" in job_properties
    assert "status" in job_properties
