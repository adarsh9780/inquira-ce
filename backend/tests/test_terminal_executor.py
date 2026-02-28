from pathlib import Path

import pytest

from app.services.terminal_executor import (
    detect_shell_command,
    normalize_workspace_cwd,
    run_workspace_terminal_command,
)


def test_detect_shell_command_returns_executable_and_args():
    shell, args = detect_shell_command()
    assert isinstance(shell, str)
    assert shell.strip() != ""
    assert isinstance(args, list)
    assert len(args) >= 1


def test_normalize_workspace_cwd_defaults_to_workspace(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    resolved = normalize_workspace_cwd(str(workspace_dir), None)
    assert resolved == str(workspace_dir.resolve())


@pytest.mark.asyncio
async def test_run_workspace_terminal_command_executes_in_workspace_dir(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    result = await run_workspace_terminal_command(
        command="echo inquira_terminal_test",
        workspace_dir=str(workspace_dir),
        timeout=30,
    )

    assert result["exit_code"] == 0
    assert "inquira_terminal_test" in result["stdout"]
    assert result["cwd"] == str(Path(workspace_dir).resolve())
