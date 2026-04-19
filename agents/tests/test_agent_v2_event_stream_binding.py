from agent_v2.events import emit_agent_event
from agent_v2.graph import _with_stream_event_emitter
from agent_v2.nodes import chat_node, route_node
from agent_v2.router import RouteDecision

from langchain_core.messages import HumanMessage
import pytest


def test_agent_v2_stream_event_binding_emits_custom_payload(monkeypatch):
    captured: list[dict] = []

    def _writer(payload):
        captured.append(payload)

    monkeypatch.setattr("langgraph.config.get_stream_writer", lambda: _writer)

    def _node(_state, _config):
        emit_agent_event("agent_status", {"message": "searching schema"})
        return {"ok": True}

    wrapped = _with_stream_event_emitter(_node)
    result = wrapped({}, {})

    assert result == {"ok": True}
    assert captured == [{"event": "agent_status", "data": {"message": "searching schema"}}]

    # Emitter is request-scoped and should not leak outside the wrapped node call.
    emit_agent_event("tool_call", {"call_id": "outside"})
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_route_node_emits_user_facing_reasoning(monkeypatch):
    captured: list[tuple[str, dict]] = []

    async def _fake_decide_route_details(_messages, _configurable):
        return RouteDecision(
            route="analysis",
            reasoning="I understand you want compare batting metrics, so I need inspect data context before answering.",
        )

    monkeypatch.setattr("agent_v2.nodes.decide_route_details", _fake_decide_route_details)
    monkeypatch.setattr("agent_v2.nodes.emit_agent_event", lambda event, payload: captured.append((event, payload)))

    result = await route_node({"messages": []}, {"configurable": {}})

    assert result["route"] == "analysis"
    assert result["metadata"] == {"is_safe": True, "is_relevant": True}
    assert captured == [
        (
            "reasoning",
            {
                "stage": "intent",
                "message": "I understand you want compare batting metrics, so I need inspect data context before answering.",
                "route": "analysis",
            },
        )
    ]


@pytest.mark.asyncio
async def test_route_node_prefers_workspace_table_description_before_router(monkeypatch):
    async def _should_not_call_router(_messages, _configurable):
        raise AssertionError("router should be skipped for strong schema description matches")

    monkeypatch.setattr("agent_v2.nodes.decide_route_details", _should_not_call_router)

    result = await route_node(
        {
            "messages": [HumanMessage(content="give me top 10 batsman")],
            "table_names": ["batting", "sales"],
            "workspace_schema": {
                "tables": [
                    {
                        "table_name": "batting",
                        "context": "Batting scorecards for cricket matches.",
                        "columns": [{"name": "batsman", "description": "Player batting name"}],
                    },
                    {
                        "table_name": "sales",
                        "context": "Retail invoices by store.",
                        "columns": [{"name": "amount", "description": "Sale amount"}],
                    },
                ]
            },
        },
        {"configurable": {}},
    )

    assert result["route"] == "analysis"
    assert result["table_names"] == ["batting"]
    relevance = result["metadata"]["schema_relevance"]
    assert relevance["strong_match"] is True
    assert relevance["matched_tables"][0]["source"] == "table_description"


@pytest.mark.asyncio
async def test_route_node_uses_column_metadata_when_table_description_is_ambiguous(monkeypatch):
    async def _should_not_call_router(_messages, _configurable):
        raise AssertionError("router should be skipped for strong column metadata matches")

    monkeypatch.setattr("agent_v2.nodes.decide_route_details", _should_not_call_router)

    result = await route_node(
        {
            "messages": [HumanMessage(content="top 10 batsman")],
            "table_names": ["deliveries", "stores"],
            "workspace_schema": {
                "tables": [
                    {
                        "table_name": "deliveries",
                        "context": "Ball by ball events.",
                        "columns": [{"name": "batsman", "description": "Batter facing delivery"}],
                    },
                    {
                        "table_name": "stores",
                        "context": "Store performance.",
                        "columns": [{"name": "store_name", "description": "Retail store"}],
                    },
                ]
            },
        },
        {"configurable": {}},
    )

    assert result["route"] == "analysis"
    assert result["table_names"] == ["deliveries"]
    assert result["metadata"]["schema_relevance"]["matched_tables"][0]["source"] == "column_metadata"


@pytest.mark.asyncio
async def test_route_node_marks_table_clarification_when_no_schema_match(monkeypatch):
    async def _fake_decide_route_details(_messages, _configurable):
        return RouteDecision(route="general_chat", reasoning="I can answer directly.")

    monkeypatch.setattr("agent_v2.nodes.decide_route_details", _fake_decide_route_details)

    result = await route_node(
        {
            "messages": [HumanMessage(content="give me top 10 batsman")],
            "table_names": ["orders", "customers"],
            "workspace_schema": {
                "tables": [
                    {"table_name": "orders", "context": "Retail orders.", "columns": []},
                    {"table_name": "customers", "context": "Customer profiles.", "columns": []},
                ]
            },
        },
        {"configurable": {}},
    )

    assert result["route"] == "general_chat"
    assert result["metadata"]["needs_table_clarification"] is True
    assert result["metadata"]["available_tables"] == ["orders", "customers"]


@pytest.mark.asyncio
async def test_chat_node_returns_table_clarification_without_model_call(monkeypatch):
    def _should_not_get_model(_config, *, lite):
        _ = lite
        raise AssertionError("clarification response should not call a model")

    monkeypatch.setattr("agent_v2.nodes._get_model", _should_not_get_model)

    result = await chat_node(
        {
            "messages": [HumanMessage(content="give me top 10 batsman")],
            "metadata": {
                "needs_table_clarification": True,
                "available_tables": ["orders", "customers"],
            },
        },
        {"configurable": {}},
    )

    assert result["route"] == "general_chat"
    assert "Which table should I use?" in result["final_explanation"]
    assert "orders, customers" in result["final_explanation"]
