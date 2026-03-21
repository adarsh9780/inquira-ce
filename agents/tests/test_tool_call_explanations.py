from __future__ import annotations

import pytest
import httpx

from agent_v2.tools.execute_python import execute_python
from agent_v2.tools.search_schema import search_schema


def test_search_schema_tool_call_event_includes_explanation(monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        "agent_v2.tools.search_schema.emit_agent_event",
        lambda event, payload: captured.append((event, payload)),
    )

    result = search_schema(
        schema={
            "tables": [
                {
                    "table_name": "orders",
                    "columns": [{"name": "revenue", "dtype": "DOUBLE", "description": "Order revenue"}],
                }
            ]
        },
        data_path=None,
        table_names=["orders"],
        query="revenue",
        queries=["revenue"],
        table_name="orders",
        max_results=10,
        explanation="I need schema matches before I write code.",
        emit_tool_events=True,
    )

    assert result["match_count"] == 1
    assert captured[0][0] == "tool_call"
    assert captured[0][1]["explanation"] == "I need schema matches before I write code."


@pytest.mark.asyncio
async def test_execute_python_tool_call_event_includes_explanation(monkeypatch) -> None:
    captured: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        "agent_v2.tools.execute_python.emit_agent_event",
        lambda event, payload: captured.append((event, payload)),
    )
    class _Client:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        async def post(self, url, json=None, headers=None):
            assert url == "http://localhost:8000/api/v1/internal/agent/workspaces/ws1/execute"
            assert json == {"code": "print('ok')", "timeout": 5}
            assert headers["Authorization"] == "Bearer test-secret"
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "stdout": "ok",
                    "stderr": "",
                    "error": None,
                    "result": None,
                    "result_type": None,
                    "result_kind": "none",
                    "result_name": None,
                    "variables": {"dataframes": {}, "figures": {}, "scalars": {}},
                    "artifacts": [],
                },
            )

    monkeypatch.setattr("agent_v2.tools.execute_python.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "agent_v2.tools.execute_python.load_agent_runtime_config",
        lambda: type(
            "_Cfg",
            (),
            {"backend_base_url": "http://localhost:8000", "backend_shared_secret": "test-secret"},
        )(),
    )

    result = await execute_python(
        workspace_id="ws1",
        data_path=__file__,
        code="print('ok')",
        timeout=5,
        explanation="I have candidate code and need to verify it runs.",
        emit_tool_events=True,
    )

    assert result["success"] is True
    assert captured[0][0] == "tool_call"
    assert captured[0][1]["explanation"] == "I have candidate code and need to verify it runs."


@pytest.mark.asyncio
async def test_execute_python_uses_workspace_kernel_error_payload_on_http_failure(monkeypatch) -> None:
    class _Client:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        async def post(self, url, json=None, headers=None):
            _ = (url, json, headers)
            return httpx.Response(404, json={"detail": "Workspace not found"})

    monkeypatch.setattr("agent_v2.tools.execute_python.httpx.AsyncClient", _Client)
    monkeypatch.setattr(
        "agent_v2.tools.execute_python.load_agent_runtime_config",
        lambda: type(
            "_Cfg",
            (),
            {"backend_base_url": "http://localhost:8000", "backend_shared_secret": "test-secret"},
        )(),
    )

    result = await execute_python(
        workspace_id="missing",
        data_path=__file__,
        code="print('x')",
        timeout=5,
        explanation="Running code in the workspace kernel next.",
        emit_tool_events=False,
    )

    assert result["success"] is False
    assert result["error"] == "Workspace not found"
