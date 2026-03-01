from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_terminal_execute_rejects_when_terminal_disabled(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_require_workspace_access(session, user_id, workspace_id):
        _ = (session, user_id, workspace_id)
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    monkeypatch.setattr(runtime_api, "_require_workspace_access", fake_require_workspace_access)
    monkeypatch.setattr(
        runtime_api,
        "load_execution_runtime_config",
        lambda: SimpleNamespace(
            terminal_enabled=False,
            terminal_command_allowlist=[],
            terminal_command_denylist=[],
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await runtime_api.execute_workspace_terminal_command(
            workspace_id="ws-1",
            payload=runtime_api.TerminalExecuteRequest(command="pwd", cwd=None, timeout=30),
            session=object(),
            current_user=SimpleNamespace(id="user-1"),
        )

    assert exc.value.status_code == 403
    assert "terminal feature is disabled" in str(exc.value.detail).lower()
