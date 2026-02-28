from pathlib import Path

import pytest

from app.services.terminal_executor import (
    detect_shell_command,
    normalize_workspace_cwd,
    run_workspace_terminal_command,
    shutdown_terminal_sessions,
)


@pytest.fixture(autouse=True)
async def _cleanup_terminal_sessions():
    # Ensure subprocess-backed terminal sessions are closed on the same event loop
    # used by async tests to avoid event-loop-closed transport warnings.
    await shutdown_terminal_sessions()
    yield
    await shutdown_terminal_sessions()


def test_detect_shell_command_returns_executable_and_args():
    shell, args = detect_shell_command()
    assert isinstance(shell, str)
    assert shell.strip() != ""
    assert isinstance(args, list)


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
        user_id="user-1",
        workspace_id="ws-1",
        command="echo inquira_terminal_test",
        workspace_dir=str(workspace_dir),
        timeout=30,
    )

    assert result["exit_code"] == 0
    assert "inquira_terminal_test" in result["stdout"]
    assert result["cwd"] == str(Path(workspace_dir).resolve())


@pytest.mark.asyncio
async def test_run_workspace_terminal_command_persists_shell_session_state(tmp_path):
    workspace_dir = tmp_path / "workspace_state"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    first = await run_workspace_terminal_command(
        user_id="user-1",
        workspace_id="ws-persist",
        command="export INQ_TEST_VAR=12345",
        workspace_dir=str(workspace_dir),
        timeout=30,
    )
    second = await run_workspace_terminal_command(
        user_id="user-1",
        workspace_id="ws-persist",
        command="echo $INQ_TEST_VAR",
        workspace_dir=str(workspace_dir),
        timeout=30,
    )

    assert first["exit_code"] == 0
    assert second["exit_code"] == 0
    assert "12345" in second["stdout"]
