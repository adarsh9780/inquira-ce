from app.v1.services.workspace_service import WorkspaceService


def test_workspace_name_normalization_is_case_insensitive_and_trimmed():
    assert WorkspaceService.normalize_name("  Sales Team  ") == "sales team"
    assert WorkspaceService.normalize_name("SaLeS   Team") == "sales team"
