from pathlib import Path

import pytest

from app.services.terminal_executor import (
    _CWD_RE,
    TerminalSessionManager,
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


def _shell_mode() -> str:
    _shell, _args, mode = TerminalSessionManager.detect_shell_command()
    return mode


def _print_cwd_command() -> str:
    mode = _shell_mode()
    if mode == "powershell":
        return "Write-Output $PWD.Path"
    if mode == "cmd":
        return "echo %CD%"
    return "pwd"


def _set_env_command(name: str, value: str) -> str:
    mode = _shell_mode()
    if mode == "powershell":
        return f"$env:{name} = '{value}'"
    if mode == "cmd":
        return f"set {name}={value}"
    return f"export {name}={value}"


def _print_env_command(name: str) -> str:
    mode = _shell_mode()
    if mode == "powershell":
        return f"Write-Output $env:{name}"
    if mode == "cmd":
        return f"echo %{name}%"
    return f"printf '%s\\n' \"${name}\""


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


def test_powershell_wrapper_uses_explicit_marker_concatenation():
    payload = TerminalSessionManager()._wrap_command(
        mode="powershell",
        command="Write-Output hello",
        token="abc123",
    )

    assert "Write-Output ('__INQUIRA_DONE__abc123__' + $__inq_exit)" in payload
    assert "Write-Output ('__INQUIRA_CWD__abc123__' + $__inq_cwd)" in payload


def test_cwd_marker_parser_ignores_echoed_powershell_wrapper_source():
    echoed_wrapper_line = "Write-Output ('__INQUIRA_CWD__abc123__' + $__inq_cwd)"
    actual_marker_line = "__INQUIRA_CWD__abc123__C:\\workspace"

    assert _CWD_RE.fullmatch(echoed_wrapper_line) is None
    match = _CWD_RE.fullmatch(actual_marker_line)
    assert match is not None
    assert match.group("cwd") == "C:\\workspace"


@pytest.mark.asyncio
async def test_run_workspace_terminal_command_executes_in_workspace_dir(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    result = await run_workspace_terminal_command(
        user_id="user-1",
        workspace_id="ws-1",
        command=_print_cwd_command(),
        workspace_dir=str(workspace_dir),
        timeout=30,
    )

    assert result["exit_code"] == 0
    expected_cwd = str(Path(workspace_dir).resolve())
    assert expected_cwd in result["stdout"]
    assert result["cwd"] == expected_cwd


@pytest.mark.asyncio
async def test_run_workspace_terminal_command_persists_shell_session_state(tmp_path):
    workspace_dir = tmp_path / "workspace_state"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    first = await run_workspace_terminal_command(
        user_id="user-1",
        workspace_id="ws-persist",
        command=_set_env_command("INQ_TEST_VAR", "12345"),
        workspace_dir=str(workspace_dir),
        timeout=30,
    )
    second = await run_workspace_terminal_command(
        user_id="user-1",
        workspace_id="ws-persist",
        command=_print_env_command("INQ_TEST_VAR"),
        workspace_dir=str(workspace_dir),
        timeout=30,
    )

    assert first["exit_code"] == 0
    assert second["exit_code"] == 0
    assert "12345" in second["stdout"]
