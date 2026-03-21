from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.v1.api import internal_agent_router as internal_api


def test_agent_runtime_internal_auth_rejects_invalid_secret(monkeypatch):
    monkeypatch.setenv("INQUIRA_AGENT_SHARED_SECRET", "top-secret")

    with pytest.raises(HTTPException) as exc:
        internal_api._require_agent_runtime_auth("Bearer wrong-secret")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_agent_runtime_internal_execute_uses_workspace_id_to_target_kernel(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-internal"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    async def fake_get_any_by_id(session, workspace_id):
        _ = session
        assert workspace_id == "ws-1"
        return SimpleNamespace(duckdb_path=str(duckdb_path))

    captured = {}

    async def fake_execute_impl(*, workspace_id, workspace_duckdb_path, payload):
        captured["workspace_id"] = workspace_id
        captured["workspace_duckdb_path"] = workspace_duckdb_path
        captured["code"] = payload.code
        captured["timeout"] = payload.timeout
        return internal_api.ExecuteResponse(
            success=True,
            run_id="run-1",
            stdout="ok",
            stderr="",
            has_stdout=True,
            has_stderr=False,
            error=None,
            result=None,
            result_type=None,
            result_kind="none",
            result_name=None,
            variables={"dataframes": {}, "figures": {}, "scalars": {}},
            artifacts=[],
        )

    monkeypatch.setattr(
        "app.v1.api.internal_agent_router.WorkspaceRepository.get_any_by_id",
        fake_get_any_by_id,
    )
    monkeypatch.setattr(
        "app.v1.api.internal_agent_router._execute_workspace_code_impl",
        fake_execute_impl,
    )

    response = await internal_api.execute_workspace_code_for_agent(
        workspace_id="ws-1",
        payload=internal_api.ExecuteRequest(code="print('ok')", timeout=15),
        session=object(),
    )

    assert response.success is True
    assert captured["workspace_id"] == "ws-1"
    assert captured["workspace_duckdb_path"] == str(duckdb_path)
    assert captured["code"] == "print('ok')"
    assert captured["timeout"] == 15
