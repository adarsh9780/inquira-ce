import pytest

from app.services.terminal_executor import TerminalSessionManager


def test_resolve_workspace_cwd_blocks_escape(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    nested = workspace_dir / "nested"
    nested.mkdir(parents=True, exist_ok=True)

    resolved = TerminalSessionManager.resolve_workspace_cwd(
        workspace_dir=str(workspace_dir),
        cwd="nested",
        current_cwd=str(workspace_dir),
    )
    assert resolved == str(nested.resolve())

    with pytest.raises(PermissionError):
        TerminalSessionManager.resolve_workspace_cwd(
            workspace_dir=str(workspace_dir),
            cwd="../../",
            current_cwd=str(workspace_dir),
        )
