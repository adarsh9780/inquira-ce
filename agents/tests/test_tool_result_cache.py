from __future__ import annotations

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
