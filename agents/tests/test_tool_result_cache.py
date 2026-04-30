from __future__ import annotations

import asyncio
import os

import pytest

from agent_v2 import nodes


@pytest.mark.asyncio
async def test_execute_pending_tools_deduplicates_cacheable_calls(monkeypatch) -> None:
    calls: list[dict] = []
    events: list[tuple[str, dict]] = []

    async def fake_search(_state, args, _explanation):
        calls.append(args)
        return {"columns": [{"name": "customer_name"}], "match_count": 1}

    monkeypatch.setattr(nodes, "emit_agent_event", lambda event, payload: events.append((event, payload)))

    state = {
        "workspace_id": "ws-1",
        "analysis_context": {"schema_manifest": {"schema_version": "schema-v1"}},
        "pending_tools": [
            {"tool": "search_schema", "args": {"queries": ["customer"], "limit": 20}},
            {"tool": "search_schema", "args": {"queries": ["customer"], "limit": 20}},
        ],
    }

    result = await nodes.execute_pending_tools_node(
        state,
        {},
        message_key="analysis_tool_messages",
        registry={"search_schema": fake_search},
    )

    assert calls == [{"queries": ["customer"], "limit": 20}]
    assert len(result["analysis_tool_messages"]) == 2
    assert len(result["tool_result_cache"]) == 1
    assert any(event == "tool_cache_hit" for event, _payload in events)


@pytest.mark.asyncio
async def test_execute_pending_tools_reuses_existing_cache(monkeypatch) -> None:
    calls: list[dict] = []
    events: list[tuple[str, dict]] = []

    async def fake_search(_state, args, _explanation):
        calls.append(args)
        return {"columns": []}

    monkeypatch.setattr(nodes, "emit_agent_event", lambda event, payload: events.append((event, payload)))
    state = {
        "workspace_id": "ws-1",
        "analysis_context": {"schema_manifest": {"schema_version": "schema-v1"}},
        "pending_tools": [{"tool": "search_schema", "args": {"queries": ["revenue"]}}],
    }
    key = nodes._normalized_tool_cache_key(state, "search_schema", {"queries": ["revenue"]})
    state["tool_result_cache"] = {key: {"columns": [{"name": "revenue"}], "match_count": 1}}

    result = await nodes.execute_pending_tools_node(
        state,
        {},
        message_key="analysis_tool_messages",
        registry={"search_schema": fake_search},
    )

    assert calls == []
    assert len(result["analysis_tool_messages"]) == 1
    assert result["tool_result_cache"] == state["tool_result_cache"]
    assert any(event == "tool_cache_hit" for event, _payload in events)


@pytest.mark.asyncio
async def test_execute_pending_tools_keeps_runtime_tools_sequential(monkeypatch) -> None:
    active = 0
    max_active = 0

    async def fake_runtime(_state, _args, _explanation):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {"success": True}

    monkeypatch.setattr(nodes, "emit_agent_event", lambda _event, _payload: None)
    state = {
        "workspace_id": "ws-1",
        "analysis_context": {"schema_manifest": {"schema_version": "schema-v1"}},
        "pending_tools": [
            {"tool": "execute_python_runtime", "args": {"code": "print(1)"}},
            {"tool": "execute_python_runtime", "args": {"code": "print(2)"}},
        ],
    }

    result = await nodes.execute_pending_tools_node(
        state,
        {},
        message_key="analysis_runtime_tool_messages",
        registry={"execute_python_runtime": fake_runtime},
    )

    assert len(result["analysis_runtime_tool_messages"]) == 2
    assert max_active == 1


def test_sample_data_cache_key_changes_when_dataset_mtime_changes(tmp_path) -> None:
    db_path = tmp_path / "workspace.duckdb"
    db_path.write_text("db", encoding="utf-8")
    state = {
        "workspace_id": "ws-1",
        "analysis_context": {
            "data_path": str(db_path),
            "schema_manifest": {"schema_version": "schema-v1"},
        },
    }
    args = {"table_name": "orders", "limit": 5}

    first_key = nodes._normalized_tool_cache_key(state, "sample_data", args)
    initial_mtime = db_path.stat().st_mtime_ns
    updated_mtime = initial_mtime + 1_000_000
    os.utime(db_path, ns=(updated_mtime, updated_mtime))
    second_key = nodes._normalized_tool_cache_key(state, "sample_data", args)

    assert first_key != second_key
