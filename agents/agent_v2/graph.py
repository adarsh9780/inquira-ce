"""Agent v2 graph for external runtime service."""

from __future__ import annotations

from functools import wraps
import inspect
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from .events import reset_agent_event_emitter, set_agent_event_emitter
from .nodes import (
    analysis_assess_context_node,
    analysis_assess_to_next,
    analysis_collect_context_node,
    analysis_enrich_context_node,
    analysis_execute_code_node,
    analysis_execute_to_next,
    analysis_finalize_failure_node,
    analysis_finalize_success_node,
    analysis_generate_code_node,
    analysis_generate_to_next,
    analysis_guard_code_node,
    analysis_guard_to_next,
    analysis_retry_decider_node,
    analysis_retry_to_next,
    analysis_validate_result_node,
    analysis_validate_to_next,
    chat_node,
    finalize_node,
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
    table_names: list[str]
    data_path: str
    scratchpad_path: str
    context: str
    workspace_schema: dict[str, Any]
    current_code: str
    previous_code: str
    run_id: str
    known_columns: list[dict[str, str]]
    attachments: list[dict[str, str]]


def _prepare_input_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    raw_table_names = state.get("table_names")
    table_names = [str(item).strip() for item in raw_table_names] if isinstance(raw_table_names, list) else []
    table_names = [item for item in table_names if item]

    messages = state.get("messages")
    if isinstance(messages, list) and messages and not str(state.get("question") or "").strip():
        return {
            "messages": messages,
            "workspace_id": str(state.get("workspace_id") or ""),
            "user_id": str(state.get("user_id") or ""),
            "table_names": table_names,
            "data_path": str(state.get("data_path") or "") or None,
            "scratchpad_path": str(state.get("scratchpad_path") or "") or None,
            "run_id": str(state.get("run_id") or ""),
            "system_info": state.get("system_info") if isinstance(state.get("system_info"), dict) else {},
            "context": str(state.get("context") or ""),
            "workspace_schema": state.get("workspace_schema") if isinstance(state.get("workspace_schema"), dict) else {},
            "previous_code": str(state.get("previous_code") or state.get("current_code") or ""),
            "current_code": str(state.get("current_code") or ""),
            "known_columns": state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
            "attachments": state.get("attachments") if isinstance(state.get("attachments"), list) else [],
        }

    prepared = build_input_state(
        question=str(state.get("question") or ""),
        current_code=str(state.get("current_code") or ""),
        table_names=table_names,
        data_path=str(state.get("data_path") or ""),
        context=str(state.get("context") or ""),
        workspace_schema=state.get("workspace_schema") if isinstance(state.get("workspace_schema"), dict) else {},
        workspace_id=str(state.get("workspace_id") or ""),
        user_id=str(state.get("user_id") or ""),
        scratchpad_path=str(state.get("scratchpad_path") or ""),
        known_columns=state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
        attachments=state.get("attachments") if isinstance(state.get("attachments"), list) else [],
        run_id=str(state.get("run_id") or "").strip() or None,
    )
    return dict(prepared)


def _with_stream_event_emitter(fn):
    """Bind agent event emitter to LangGraph custom stream writer for this node run."""

    @wraps(fn)
    async def _async_wrapped(*args, **kwargs):
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        token = set_agent_event_emitter(
            lambda event, payload: writer({"event": str(event), "data": dict(payload or {})})
        )
        try:
            return await fn(*args, **kwargs)
        finally:
            reset_agent_event_emitter(token)

    @wraps(fn)
    def _sync_wrapped(*args, **kwargs):
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        token = set_agent_event_emitter(
            lambda event, payload: writer({"event": str(event), "data": dict(payload or {})})
        )
        try:
            return fn(*args, **kwargs)
        finally:
            reset_agent_event_emitter(token)

    return _async_wrapped if inspect.iscoroutinefunction(fn) else _sync_wrapped


def build_graph(config: RunnableConfig) -> CompiledStateGraph:
    _ = config
    init_phoenix_tracing()
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(AgentState, input_schema=RuntimeInput, output_schema=AgentOutput)
    builder.add_node("prepare_input", _with_stream_event_emitter(_prepare_input_node))
    builder.add_node("route", _with_stream_event_emitter(route_node))
    builder.add_node("analysis_collect_context", _with_stream_event_emitter(analysis_collect_context_node))
    builder.add_node("analysis_assess_context", _with_stream_event_emitter(analysis_assess_context_node))
    builder.add_node("analysis_enrich_context", _with_stream_event_emitter(analysis_enrich_context_node))
    builder.add_node("analysis_generate_code", _with_stream_event_emitter(analysis_generate_code_node))
    builder.add_node("analysis_guard_code", _with_stream_event_emitter(analysis_guard_code_node))
    builder.add_node("analysis_execute_code", _with_stream_event_emitter(analysis_execute_code_node))
    builder.add_node("analysis_retry_decider", _with_stream_event_emitter(analysis_retry_decider_node))
    builder.add_node("analysis_validate_result", _with_stream_event_emitter(analysis_validate_result_node))
    builder.add_node("analysis_finalize_success", _with_stream_event_emitter(analysis_finalize_success_node))
    builder.add_node("analysis_finalize_failure", _with_stream_event_emitter(analysis_finalize_failure_node))
    builder.add_node("chat", _with_stream_event_emitter(chat_node))
    builder.add_node("reject", _with_stream_event_emitter(reject_node))
    builder.add_node("finalize", _with_stream_event_emitter(finalize_node))

    builder.add_edge(START, "prepare_input")
    builder.add_edge("prepare_input", "route")
    builder.add_conditional_edges(
        "route",
        route_to_next,
        {
            "analysis_collect_context": "analysis_collect_context",
            "chat": "chat",
            "reject": "reject",
        },
    )
    builder.add_edge("analysis_collect_context", "analysis_assess_context")
    builder.add_conditional_edges(
        "analysis_assess_context",
        analysis_assess_to_next,
        {
            "analysis_enrich_context": "analysis_enrich_context",
            "analysis_generate_code": "analysis_generate_code",
        },
    )
    builder.add_edge("analysis_enrich_context", "analysis_generate_code")
    builder.add_conditional_edges(
        "analysis_generate_code",
        analysis_generate_to_next,
        {
            "analysis_guard_code": "analysis_guard_code",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_guard_code",
        analysis_guard_to_next,
        {
            "analysis_execute_code": "analysis_execute_code",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_execute_code",
        analysis_execute_to_next,
        {
            "analysis_validate_result": "analysis_validate_result",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_retry_decider",
        analysis_retry_to_next,
        {
            "analysis_enrich_context": "analysis_enrich_context",
            "analysis_generate_code": "analysis_generate_code",
            "analysis_finalize_failure": "analysis_finalize_failure",
        },
    )
    builder.add_conditional_edges(
        "analysis_validate_result",
        analysis_validate_to_next,
        {
            "analysis_generate_code": "analysis_generate_code",
            "analysis_finalize_failure": "analysis_finalize_failure",
            "analysis_finalize_success": "analysis_finalize_success",
        },
    )
    builder.add_edge("analysis_finalize_success", "finalize")
    builder.add_edge("analysis_finalize_failure", "finalize")
    builder.add_edge("chat", "finalize")
    builder.add_edge("reject", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()
