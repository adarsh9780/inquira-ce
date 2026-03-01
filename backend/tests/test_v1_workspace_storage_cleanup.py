import pytest

from app.v1.services.workspace_storage_service import WorkspaceStorageService


@pytest.mark.asyncio
async def test_hard_delete_workspace_removes_entire_workspace_directory(monkeypatch, tmp_path):
    user_root = tmp_path / "workspaces-root"

    monkeypatch.setattr(
        WorkspaceStorageService,
        "_user_root",
        staticmethod(lambda _username: user_root),
    )

    workspace_dir = WorkspaceStorageService.build_workspace_dir("alice", "ws-1")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "workspace.duckdb").write_text("db", encoding="utf-8")
    (workspace_dir / "agent_memory.db").write_text("mem", encoding="utf-8")
    (workspace_dir / "meta").mkdir(parents=True, exist_ok=True)
    (workspace_dir / "meta" / "table_schema.json").write_text("{}", encoding="utf-8")

    assert workspace_dir.exists()

    await WorkspaceStorageService.hard_delete_workspace("alice", "ws-1")

    assert workspace_dir.exists() is False


@pytest.mark.asyncio
async def test_ensure_workspace_dirs_creates_pyproject_for_uv_commands(monkeypatch, tmp_path):
    user_root = tmp_path / "workspaces-root"
    monkeypatch.setattr(
        WorkspaceStorageService,
        "_user_root",
        staticmethod(lambda _username: user_root),
    )

    workspace_dir = await WorkspaceStorageService.ensure_workspace_dirs("alice", "ws-2")
    pyproject_path = workspace_dir / "pyproject.toml"

    assert pyproject_path.exists() is True
    content = pyproject_path.read_text(encoding="utf-8")
    assert "[project]" in content
    assert 'name = "ws-2"' in content
