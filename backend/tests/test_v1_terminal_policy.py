from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api import runtime as runtime_api


def _runtime_config(**kwargs):
    defaults = {
        "terminal_command_allowlist": [],
        "terminal_command_denylist": [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_terminal_policy_allows_uv_python_ls_grep_and_cd():
    config = _runtime_config()
    runtime_api._enforce_terminal_command_policy("uv add pandas", config)
    runtime_api._enforce_terminal_command_policy("python -V", config)
    runtime_api._enforce_terminal_command_policy("ls | grep py", config)
    runtime_api._enforce_terminal_command_policy("cd src", config)


def test_terminal_policy_blocks_disallowed_commands():
    config = _runtime_config()
    with pytest.raises(HTTPException):
        runtime_api._enforce_terminal_command_policy("rm -rf .", config)


def test_terminal_policy_blocks_chaining_and_redirection():
    config = _runtime_config()
    with pytest.raises(HTTPException):
        runtime_api._enforce_terminal_command_policy("ls && grep py", config)
    with pytest.raises(HTTPException):
        runtime_api._enforce_terminal_command_policy("ls > out.txt", config)


def test_terminal_policy_rejects_cd_with_multiple_args():
    config = _runtime_config()
    with pytest.raises(HTTPException):
        runtime_api._enforce_terminal_command_policy("cd src nested", config)


def test_validate_terminal_cwd_rejects_workspace_escape(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    inside = workspace_dir / "src"
    inside.mkdir(parents=True, exist_ok=True)

    runtime_api._validate_terminal_cwd("src", str(workspace_dir))
    with pytest.raises(HTTPException):
        runtime_api._validate_terminal_cwd("../", str(workspace_dir))
    with pytest.raises(HTTPException):
        runtime_api._validate_terminal_cwd(str(tmp_path), str(workspace_dir))
