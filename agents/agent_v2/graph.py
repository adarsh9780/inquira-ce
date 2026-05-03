"""Agent v2 graph for external runtime service."""

from __future__ import annotations

from functools import wraps
import inspect
import time
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from .events import reset_agent_event_emitter, set_agent_event_emitter
from .nodes import (
    analysis_collect_context_node,
    analysis_capture_execute_tool_result_node,
    analysis_capture_sample_tool_result_node,
    analysis_enrich_to_next,
    analysis_enrich_context_node,
    analysis_enrich_context_tools_node,
    analysis_finalize_context_enrichment_node,
    analysis_execute_to_next,
    analysis_finalize_failure_node,
    analysis_finalize_success_node,
    analysis_prepare_sample_to_next,
    analysis_prepare_sample_tool_node,
    analysis_generate_code_node,
    analysis_generate_to_next,
    analysis_guard_code_node,
    analysis_guard_to_next,
    analysis_request_execute_to_next,
    analysis_request_execute_tool_node,
    analysis_request_validate_result_tool_node,
    analysis_request_validate_to_next,
    analysis_retry_decider_node,
    analysis_retry_to_next,
    analysis_runtime_tools_node,
    analysis_runtime_tools_to_next,
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
    schema_folder_path: str
    current_code: str
    previous_code: str
    run_id: str
    known_columns: list[dict[str, str]]
    attachments: list[dict[str, str]]
    privacy: dict[str, Any]


class CustomToolNode:
    """Execute structured pending tools and emit ToolMessages plus trace events."""

    def __init__(self, handler):
        self._handler = handler

    async def __call__(self, state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
        return await self._handler(state, config)


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
            "schema_folder_path": str(state.get("schema_folder_path") or ""),
            "previous_code": str(state.get("previous_code") or state.get("current_code") or ""),
            "current_code": str(state.get("current_code") or ""),
            "known_columns": state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
            "attachments": state.get("attachments") if isinstance(state.get("attachments"), list) else [],
            "privacy": state.get("privacy") if isinstance(state.get("privacy"), dict) else {},
        }

    prepared = build_input_state(
        question=str(state.get("question") or ""),
        current_code=str(state.get("current_code") or ""),
        table_names=table_names,
        data_path=str(state.get("data_path") or ""),
        context=str(state.get("context") or ""),
        workspace_schema=state.get("workspace_schema") if isinstance(state.get("workspace_schema"), dict) else {},
        schema_folder_path=str(state.get("schema_folder_path") or ""),
        workspace_id=str(state.get("workspace_id") or ""),
        user_id=str(state.get("user_id") or ""),
        scratchpad_path=str(state.get("scratchpad_path") or ""),
        known_columns=state.get("known_columns") if isinstance(state.get("known_columns"), list) else [],
        attachments=state.get("attachments") if isinstance(state.get("attachments"), list) else [],
        privacy=state.get("privacy") if isinstance(state.get("privacy"), dict) else {},
        run_id=str(state.get("run_id") or "").strip() or None,
    )
    return dict(prepared)


def _with_stream_event_emitter(fn):
    """Bind agent event emitter to LangGraph custom stream writer for this node run."""

    target = fn
    if not inspect.isfunction(fn) and not inspect.ismethod(fn) and callable(fn):
        target = getattr(fn, "__call__", fn)
    node_name = str(getattr(target, "__name__", "") or getattr(fn, "__class__", type(fn)).__name__)

    def _attach_node_timing(result: Any, args: tuple[Any, ...], duration_ms: int) -> Any:
        if not isinstance(result, dict):
            return result
        state = args[0] if args and isinstance(args[0], dict) else {}
        state_metadata = state.get("metadata") if isinstance(state.get("metadata"), dict) else {}
        result_metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        metadata = {**state_metadata, **result_metadata}
        state_timings = (
            state_metadata.get("agent_timings")
            if isinstance(state_metadata.get("agent_timings"), dict)
            else {}
        )
        result_timings = (
            result_metadata.get("agent_timings")
            if isinstance(result_metadata.get("agent_timings"), dict)
            else {}
        )
        timings = {**state_timings, **result_timings}
        nodes = dict(timings.get("nodes") or {}) if isinstance(timings.get("nodes"), dict) else {}
        nodes[node_name] = duration_ms
        return {
            **result,
            "metadata": {
                **metadata,
                "agent_timings": {
                    **timings,
                    "nodes": nodes,
                },
            },
        }

    @wraps(fn)
    async def _async_wrapped(*args, **kwargs):
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        token = set_agent_event_emitter(
            lambda event, payload: writer({"event": str(event), "data": dict(payload or {})})
        )
        started = time.perf_counter()
        try:
            result = await fn(*args, **kwargs)
            duration_ms = max(1, int((time.perf_counter() - started) * 1000))
            writer(
                {
                    "event": "node_timing",
                    "data": {"node": node_name, "duration_ms": duration_ms},
                }
            )
            return _attach_node_timing(result, args, duration_ms)
        finally:
            reset_agent_event_emitter(token)

    @wraps(fn)
    def _sync_wrapped(*args, **kwargs):
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        token = set_agent_event_emitter(
            lambda event, payload: writer({"event": str(event), "data": dict(payload or {})})
        )
        started = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            duration_ms = max(1, int((time.perf_counter() - started) * 1000))
            writer(
                {
                    "event": "node_timing",
                    "data": {"node": node_name, "duration_ms": duration_ms},
                }
            )
            return _attach_node_timing(result, args, duration_ms)
        finally:
            reset_agent_event_emitter(token)

    return _async_wrapped if inspect.iscoroutinefunction(target) else _sync_wrapped


def build_graph(config: RunnableConfig) -> CompiledStateGraph:
    _ = config
    init_phoenix_tracing()
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(AgentState, input_schema=RuntimeInput, output_schema=AgentOutput)
    builder.add_node("prepare_input", _with_stream_event_emitter(_prepare_input_node))
    builder.add_node("route", _with_stream_event_emitter(route_node))
    builder.add_node("analysis_collect_context", _with_stream_event_emitter(analysis_collect_context_node))
    builder.add_node("analysis_enrich_context", _with_stream_event_emitter(analysis_enrich_context_node))
    builder.add_node(
        "analysis_enrich_context_tools",
        _with_stream_event_emitter(CustomToolNode(analysis_enrich_context_tools_node)),
    )
    builder.add_node(
        "analysis_finalize_context_enrichment",
        _with_stream_event_emitter(analysis_finalize_context_enrichment_node),
    )
    builder.add_node("analysis_prepare_sample_tool", _with_stream_event_emitter(analysis_prepare_sample_tool_node))
    builder.add_node(
        "analysis_capture_sample_tool_result",
        _with_stream_event_emitter(analysis_capture_sample_tool_result_node),
    )
    builder.add_node("analysis_generate_code", _with_stream_event_emitter(analysis_generate_code_node))
    builder.add_node("analysis_guard_code", _with_stream_event_emitter(analysis_guard_code_node))
    builder.add_node("analysis_request_execute_tool", _with_stream_event_emitter(analysis_request_execute_tool_node))
    builder.add_node(
        "analysis_capture_execute_tool_result",
        _with_stream_event_emitter(analysis_capture_execute_tool_result_node),
    )
    builder.add_node(
        "analysis_request_validate_result_tool",
        _with_stream_event_emitter(analysis_request_validate_result_tool_node),
    )
    builder.add_node(
        "analysis_runtime_tools",
        _with_stream_event_emitter(CustomToolNode(analysis_runtime_tools_node)),
    )
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
    builder.add_edge("analysis_collect_context", "analysis_enrich_context")
    builder.add_conditional_edges(
        "analysis_enrich_context",
        analysis_enrich_to_next,
        {
            "analysis_enrich_context_tools": "analysis_enrich_context_tools",
            "analysis_finalize_context_enrichment": "analysis_finalize_context_enrichment",
        },
    )
    builder.add_edge("analysis_enrich_context_tools", "analysis_enrich_context")
    builder.add_edge("analysis_finalize_context_enrichment", "analysis_prepare_sample_tool")
    builder.add_conditional_edges(
        "analysis_prepare_sample_tool",
        analysis_prepare_sample_to_next,
        {
            "analysis_runtime_tools": "analysis_runtime_tools",
            "analysis_generate_code": "analysis_generate_code",
        },
    )
    builder.add_conditional_edges(
        "analysis_runtime_tools",
        analysis_runtime_tools_to_next,
        {
            "analysis_capture_sample_tool_result": "analysis_capture_sample_tool_result",
            "analysis_capture_execute_tool_result": "analysis_capture_execute_tool_result",
            "analysis_validate_result": "analysis_validate_result",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_edge("analysis_capture_sample_tool_result", "analysis_generate_code")
    builder.add_conditional_edges(
        "analysis_generate_code",
        analysis_generate_to_next,
        {
            "analysis_enrich_context": "analysis_enrich_context",
            "analysis_guard_code": "analysis_guard_code",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_guard_code",
        analysis_guard_to_next,
        {
            "analysis_execute_code": "analysis_request_execute_tool",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_request_execute_tool",
        analysis_request_execute_to_next,
        {
            "analysis_runtime_tools": "analysis_runtime_tools",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_capture_execute_tool_result",
        analysis_execute_to_next,
        {
            "analysis_validate_result": "analysis_request_validate_result_tool",
            "analysis_retry_decider": "analysis_retry_decider",
        },
    )
    builder.add_conditional_edges(
        "analysis_request_validate_result_tool",
        analysis_request_validate_to_next,
        {
            "analysis_runtime_tools": "analysis_runtime_tools",
            "analysis_finalize_failure": "analysis_finalize_failure",
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
