"""Agent v2 graph for external runtime service."""

from __future__ import annotations

from typing import Any, TypedDict

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
from .services.tracing import init_phoenix_tracing
from .state import AgentOutput, AgentState, build_input_state


class RuntimeInput(TypedDict, total=False):
    question: str
    messages: list[Any]
    workspace_id: str
    user_id: str
    table_name: str
    data_path: str
    scratchpad_path: str
    context: str
    active_schema: dict[str, Any]
    current_code: str
    previous_code: str
    run_id: str
    known_columns: list[dict[str, str]]
    attachments: list[dict[str, str]]


def _prepare_input_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    messages = state.get("messages")
    if isinstance(messages, list) and messages and not str(state.get("question") or "").strip():
        return {
            "messages": messages,
            "workspace_id": str(state.get("workspace_id") or ""),
            "user_id": str(state.get("user_id") or ""),
            "table_name": str(state.get("table_name") or "") or None,
            "data_path": str(state.get("data_path") or "") or None,
            "scratchpad_path": str(state.get("scratchpad_path") or "") or None,
            "run_id": str(state.get("run_id") or ""),
            "system_info": state.get("system_info") if isinstance(state.get("system_info"), dict) else {},
            "context": str(state.get("context") or ""),
            "active_schema": state.get("active_schema") if isinstance(state.get("active_schema"), dict) else {},
            "previous_code": str(state.get("previous_code") or state.get("current_code") or ""),
            "current_code": str(state.get("current_code") or ""),
            "known_columns": state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
            "attachments": state.get("attachments") if isinstance(state.get("attachments"), list) else [],
        }

    prepared = build_input_state(
        question=str(state.get("question") or ""),
        schema=state.get("active_schema") if isinstance(state.get("active_schema"), dict) else {},
        current_code=str(state.get("current_code") or ""),
        table_name=str(state.get("table_name") or ""),
        data_path=str(state.get("data_path") or ""),
        context=str(state.get("context") or ""),
        workspace_id=str(state.get("workspace_id") or ""),
        user_id=str(state.get("user_id") or ""),
        scratchpad_path=str(state.get("scratchpad_path") or ""),
        known_columns=state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
        attachments=state.get("attachments") if isinstance(state.get("attachments"), list) else [],
        run_id=str(state.get("run_id") or "").strip() or None,
    )
    return dict(prepared)


def build_graph(config: RunnableConfig) -> CompiledStateGraph:
    _ = config
    init_phoenix_tracing()
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(AgentState, input_schema=RuntimeInput, output_schema=AgentOutput)
    builder.add_node("prepare_input", _prepare_input_node)
    builder.add_node("route", route_node)
    builder.add_node("react_loop", react_loop_node)
    builder.add_node("chat", chat_node)
    builder.add_node("reject", reject_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "prepare_input")
    builder.add_edge("prepare_input", "route")
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

    return builder.compile()
