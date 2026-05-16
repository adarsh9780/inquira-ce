from pathlib import Path

from app.services.runner_env import delete_workspace_runner_environment


def test_delete_workspace_runner_environment_removes_workspace_venv(tmp_path):
    workspace_dir = tmp_path / "workspaces" / "ws-1"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.db"
    duckdb_path.write_text("", encoding="utf-8")
    venv_dir = workspace_dir / ".venv"
    venv_dir.mkdir(parents=True, exist_ok=True)
    marker = venv_dir / "pyvenv.cfg"
    marker.write_text("home = /tmp/python\n", encoding="utf-8")

    deleted = delete_workspace_runner_environment(str(duckdb_path))

    assert deleted is True
    assert venv_dir.exists() is False


def test_delete_workspace_runner_environment_returns_false_when_missing(tmp_path):
    workspace_dir = tmp_path / "workspaces" / "ws-2"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.db"
    duckdb_path.write_text("", encoding="utf-8")

    deleted = delete_workspace_runner_environment(str(duckdb_path))

    assert deleted is False
    assert Path(duckdb_path).exists() is True
