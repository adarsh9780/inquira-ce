"""Agent v2 graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import Checkpointer, CompiledStateGraph

from .nodes import (
    chat_node,
    finalize_node,
    react_loop_node,
    reject_node,
    route_node,
    route_to_next,
)
from .state import AgentInput, AgentOutput, AgentState


def build_graph(checkpointer: Checkpointer | None = None) -> CompiledStateGraph:
    builder = StateGraph(AgentState, input_schema=AgentInput, output_schema=AgentOutput)

    builder.add_node("route", route_node)
    builder.add_node("react_loop", react_loop_node)
    builder.add_node("chat", chat_node)
    builder.add_node("reject", reject_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        route_to_next,
        {
            "react_loop": "react_loop",
            "chat": "chat",
            "reject": "reject",
        },
    )
    builder.add_edge("react_loop", "finalize")
    builder.add_edge("chat", "finalize")
    builder.add_edge("reject", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
