from __future__ import annotations

import pytest

from app.services.output_capture import build_run_wrapped_code
from app.v1.api import runtime as runtime_api


@pytest.mark.asyncio
async def test_execute_workspace_code_impl_passes_turn_context_into_wrapped_code(monkeypatch, tmp_path):
    workspace_dir = tmp_path / "ws-wrap"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    duckdb_path = workspace_dir / "workspace.duckdb"
    duckdb_path.touch()

    captured: dict[str, object] = {}

    async def fake_execute_code(**kwargs):
        captured["code"] = kwargs.get("code")
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "error": None,
            "result": None,
            "result_type": None,
            "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
            "artifacts": [],
        }

    monkeypatch.setattr(runtime_api, "execute_code", fake_execute_code)

    payload = runtime_api.ExecuteRequest(
        code="result_df = 1",
        timeout=30,
        run_id="run-stable",
        conversation_id="conv-1",
        turn_id="turn-1",
        artifact_dir="/tmp/conversations/conv-1/turn-1",
    )
    response = await runtime_api._execute_workspace_code_impl(
        workspace_id="ws-wrap",
        workspace_duckdb_path=str(duckdb_path),
        payload=payload,
    )

    assert response.success is True
    assert response.run_id == "run-stable"
    wrapped = str(captured.get("code") or "")
    assert "artifact_dir='/tmp/conversations/conv-1/turn-1'" in wrapped
    assert "conversation_id='conv-1'" in wrapped
    assert "turn_id='turn-1'" in wrapped
    assert "export_dataframe" in wrapped


def test_build_run_wrapped_code_skips_auto_capture_without_artifact_dir():
    wrapped = build_run_wrapped_code("x = 1", "run-1", [])
    assert "[auto-capture]" not in wrapped
    assert "export_dataframe" not in wrapped
