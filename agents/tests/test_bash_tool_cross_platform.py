from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_v2.tools import bash_tool


def _patch_runtime(monkeypatch, *, allowed: tuple[str, ...] | None = None) -> None:
    monkeypatch.setattr(
        bash_tool,
        "load_agent_runtime_config",
        lambda: SimpleNamespace(
            bash_allowed_commands=allowed or ("rg", "grep", "wc", "head", "tail", "ls", "cat", "find"),
            bash_max_output_chars=4000,
        ),
    )
    monkeypatch.setattr(bash_tool, "emit_agent_event", lambda *args, **kwargs: None)


def _workspace(tmp_path):
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    data_path = workspace_dir / "workspace.duckdb"
    data_path.touch()
    notes = workspace_dir / "notes.txt"
    notes.write_text("alpha\nbeta\nalpha beta\n", encoding="utf-8")
    (workspace_dir / "nested").mkdir()
    (workspace_dir / "nested" / "data.csv").write_text("col\n1\n", encoding="utf-8")
    return workspace_dir, data_path


@pytest.mark.asyncio
async def test_bash_tool_workspace_commands_are_shell_neutral(monkeypatch, tmp_path):
    _patch_runtime(monkeypatch)
    _, data_path = _workspace(tmp_path)

    ls_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="ls .",
    )
    assert ls_result["exit_code"] == 0
    assert "notes.txt" in ls_result["stdout"]

    cat_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="cat notes.txt",
    )
    assert cat_result["stdout"] == "alpha\nbeta\nalpha beta\n"

    head_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="head -n 1 notes.txt",
    )
    assert head_result["stdout"] == "alpha\n"

    tail_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="tail -n 1 notes.txt",
    )
    assert tail_result["stdout"] == "alpha beta\n"

    wc_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="wc notes.txt",
    )
    assert wc_result["exit_code"] == 0
    assert "notes.txt" in wc_result["stdout"]

    find_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="find . -name data.csv",
    )
    assert find_result["stdout"] == "nested/data.csv\n"

    grep_result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="grep -n alpha notes.txt",
    )
    assert grep_result["exit_code"] == 0
    assert "notes.txt:1:alpha" in grep_result["stdout"]


@pytest.mark.asyncio
async def test_bash_tool_blocks_workspace_escape(monkeypatch, tmp_path):
    _patch_runtime(monkeypatch)
    _, data_path = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="cat ../outside.txt",
    )

    assert result["exit_code"] == 1
    assert "workspace directory" in result["stderr"]


@pytest.mark.asyncio
async def test_bash_tool_blocks_symlink_workspace_escape(monkeypatch, tmp_path):
    _patch_runtime(monkeypatch)
    workspace_dir, data_path = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link_path = workspace_dir / "linked-secret.txt"
    try:
        link_path.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this platform: {exc}")

    result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="cat linked-secret.txt",
    )

    assert result["exit_code"] == 1
    assert "workspace directory" in result["stderr"]


@pytest.mark.asyncio
async def test_bash_tool_reports_missing_rg_without_shell(monkeypatch, tmp_path):
    _patch_runtime(monkeypatch, allowed=("rg",))
    monkeypatch.setattr(bash_tool.shutil, "which", lambda name: None)
    _, data_path = _workspace(tmp_path)

    result = await bash_tool.run_bash(
        user_id="u1",
        workspace_id="w1",
        data_path=str(data_path),
        command="rg alpha",
    )

    assert result["exit_code"] == 1
    assert "not available" in result["stderr"]
