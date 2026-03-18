"""Agent v2 graph wrapper for external runtime service."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from .nodes import (
    chat_node,
    finalize_node,
    react_loop_node,
    reject_node,
    route_node,
    route_to_next,
)
from .state import build_input_state


class AgentV2Graph:
    def __init__(self, graph: CompiledStateGraph) -> None:
        self._graph = graph

    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        input_state = build_input_state(
            question=str(state.get("question") or ""),
            schema=state.get("active_schema") if isinstance(state.get("active_schema"), dict) else {},
            current_code=str(state.get("current_code") or ""),
            table_name=str(state.get("table_name") or ""),
            data_path=str(state.get("data_path") or ""),
            context=str(state.get("context") or ""),
            workspace_id=str(state.get("workspace_id") or ""),
            user_id=str(state.get("user_id") or ""),
            scratchpad_path="",
            known_columns=state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
            attachments=state.get("attachments") if isinstance(state.get("attachments"), list) else [],
            run_id=str(state.get("run_id") or "").strip() or None,
        )
        result = await self._graph.ainvoke(input_state, config=config or {})
        return result if isinstance(result, dict) else {}

    async def astream(
        self,
        state: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        input_state = build_input_state(
            question=str(state.get("question") or ""),
            schema=state.get("active_schema") if isinstance(state.get("active_schema"), dict) else {},
            current_code=str(state.get("current_code") or ""),
            table_name=str(state.get("table_name") or ""),
            data_path=str(state.get("data_path") or ""),
            context=str(state.get("context") or ""),
            workspace_id=str(state.get("workspace_id") or ""),
            user_id=str(state.get("user_id") or ""),
            scratchpad_path="",
            known_columns=state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
            attachments=state.get("attachments") if isinstance(state.get("attachments"), list) else [],
            run_id=str(state.get("run_id") or "").strip() or None,
        )
        async for step in self._graph.astream(input_state, config=config or {}):
            yield step if isinstance(step, dict) else {"unknown": {"value": step}}

def build_graph(config: RunnableConfig) -> AgentV2Graph:
    _ = config
    from langgraph.graph import END, START, StateGraph

    from .state import AgentInput, AgentOutput, AgentState

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

    return AgentV2Graph(builder.compile())
