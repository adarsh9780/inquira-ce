from app.agent_v2.tools.execute_python import execute_python
import pytest


async def _fail_execute_code(**_kwargs):
    raise AssertionError("execute_code should not be called when workspace DB is missing")


@pytest.mark.asyncio
async def test_execute_python_returns_actionable_error_when_workspace_db_is_missing(monkeypatch, tmp_path):
    events: list[tuple[str, dict]] = []

    def fake_emit(event: str, payload: dict) -> None:
        events.append((event, payload))

    monkeypatch.setattr("app.agent_v2.tools.execute_python.emit_agent_event", fake_emit)

    missing_db = tmp_path / "workspace.db"
    result = await execute_python(
        workspace_id="ws-1",
        data_path=str(missing_db),
        code="print('hi')",
        timeout=30,
    )

    assert result["success"] is False
    assert "workspace database is missing" in str(result.get("error") or "").lower()
    assert any(event == "tool_result" and payload.get("status") == "error" for event, payload in events)
