"""Contract checks for the app's non-negotiable usability flows."""

from app.main import app


def test_openapi_contains_core_workspace_dataset_chat_and_conversation_routes():
    schema = app.openapi()
    paths = schema.get("paths", {})

    assert "/api/v1/workspaces" in paths
    assert "/api/v1/workspaces/{workspace_id}/activate" in paths
    assert "/api/v1/workspaces/{workspace_id}/summary" in paths

    assert "/api/v1/workspaces/{workspace_id}/datasets" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/browser-sync" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}/schema" in paths
    assert "/api/v1/workspaces/{workspace_id}/datasets/{table_name}/schema/regenerate" in paths

    assert "/api/v1/chat/analyze" in paths
    assert "/api/v1/chat/stream" in paths

    assert "/api/v1/workspaces/{workspace_id}/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}/clear" in paths
    assert "/api/v1/conversations/{conversation_id}" in paths
    assert "/api/v1/conversations/{conversation_id}/turns" in paths

    assert "/api/v1/workspaces/{workspace_id}/execute" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/status" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/reset" in paths
    assert "/api/v1/workspaces/{workspace_id}/kernel/restart" in paths


def test_openapi_contains_methods_for_core_user_actions():
    schema = app.openapi()
    paths = schema["paths"]

    assert "post" in paths["/api/v1/workspaces"]
    assert "put" in paths["/api/v1/workspaces/{workspace_id}/activate"]
    assert "post" in paths["/api/v1/workspaces/{workspace_id}/datasets"]
    assert "delete" in paths["/api/v1/workspaces/{workspace_id}/datasets/{table_name}"]
    assert "post" in paths["/api/v1/workspaces/{workspace_id}/datasets/browser-sync"]
    assert "post" in paths["/api/v1/chat/stream"]
    assert "post" in paths["/api/v1/workspaces/{workspace_id}/conversations"]
    assert "delete" in paths["/api/v1/conversations/{conversation_id}"]
    assert "post" in paths["/api/v1/workspaces/{workspace_id}/execute"]
