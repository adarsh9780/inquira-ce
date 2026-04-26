"""State schemas for agent v2."""

from __future__ import annotations

import os
import platform
import uuid
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import add_messages


class SystemInfo(TypedDict):
    os: str
    arch: str
    ram_gb: float
    shell: str


class AgentInput(TypedDict):
    question: str
    messages: Annotated[list[AnyMessage], add_messages]
    workspace_id: str
    user_id: str
    table_names: list[str]
    data_path: str | None
    scratchpad_path: str | None
    run_id: str
    system_info: SystemInfo
    context: str
    workspace_schema: dict[str, Any]
    schema_folder_path: str
    previous_code: str
    current_code: str
    known_columns: list[dict[str, str]]
    attachments: list[dict[str, str]]


class AgentOutput(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    final_code: str | None
    final_explanation: str | None
    result_explanation: str | None
    code_explanation: str | None
    final_execution: dict[str, Any] | None
    final_artifacts: list[dict[str, Any]]
    final_executed_code: str | None
    output_contract: list[dict[str, str]]
    known_columns: list[dict[str, str]]
    route: str
    run_id: str
    metadata: dict[str, Any]


class AgentState(AgentInput, total=False):
    route: str
    final_code: str | None
    final_explanation: str | None
    result_explanation: str | None
    code_explanation: str | None
    final_execution: dict[str, Any] | None
    final_artifacts: list[dict[str, Any]]
    final_executed_code: str | None
    output_contract: list[dict[str, str]]
    known_columns: list[dict[str, str]]
    metadata: dict[str, Any]
    tool_calls: int
    code_attempts: int
    last_error: str
    analysis_context: dict[str, Any]
    analysis_tool_messages: Annotated[list[AnyMessage], add_messages]
    analysis_runtime_tool_messages: Annotated[list[AnyMessage], add_messages]
    context_sufficiency: dict[str, Any]
    tool_plan: list[dict[str, Any]]
    pending_tools: list[dict[str, Any]]
    enrichment_hints: list[str]
    enrichment_tool_cursor: int
    runtime_tool_cursor: int
    runtime_tool_stage: str
    enrichment_results: dict[str, Any]
    candidate_code: str
    guard_result: dict[str, Any]
    execution_result: dict[str, Any]
    retry_feedback: str
    retry_target: str
    schema_memory_path: str
    validation_outcome: dict[str, Any]
    attempt_counters: dict[str, int]
    analysis_output: dict[str, Any]
    result_summary: dict[str, Any]


def default_system_info() -> SystemInfo:
    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "ram_gb": 0.0,
        "shell": os.environ.get("SHELL", ""),
    }


def build_input_state(
    *,
    question: str,
    current_code: str,
    table_names: list[str] | None,
    data_path: str,
    context: str,
    workspace_schema: dict[str, Any] | None = None,
    schema_folder_path: str = "",
    workspace_id: str,
    user_id: str,
    scratchpad_path: str,
    known_columns: list[dict[str, str]] | None = None,
    attachments: list[dict[str, str]] | None = None,
    run_id: str | None = None,
    **_: Any,
) -> AgentInput:
    normalized_table_names: list[str] = []
    seen_tables: set[str] = set()
    candidates = table_names if isinstance(table_names, list) else []
    for item in candidates:
        candidate = str(item or "").strip()
        if not candidate:
            continue
        dedupe = candidate.lower()
        if dedupe in seen_tables:
            continue
        seen_tables.add(dedupe)
        normalized_table_names.append(candidate)

    normalized_known_columns: list[dict[str, str]] = []
    for item in known_columns or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        normalized_known_columns.append(
            {
                "table_name": str(item.get("table_name") or "").strip(),
                "name": name,
                "dtype": str(item.get("dtype") or "").strip(),
                "description": str(item.get("description") or "").strip(),
            }
        )

    normalized_attachments: list[dict[str, str]] = []
    content_blocks: list[dict[str, Any]] = []
    if str(question or "").strip():
        content_blocks.append({"type": "text", "text": str(question)})
    for item in attachments or []:
        if not isinstance(item, dict):
            continue
        attachment_id = str(item.get("attachment_id") or "").strip()
        media_type = str(item.get("media_type") or "").strip()
        filename = str(item.get("filename") or "").strip()
        data_base64 = str(item.get("data_base64") or "").strip()
        if not attachment_id or not media_type or not filename or not data_base64:
            continue
        normalized_attachments.append(
            {
                "attachment_id": attachment_id,
                "media_type": media_type,
                "filename": filename,
                "data_base64": data_base64,
            }
        )
        content_blocks.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{data_base64}",
                },
            }
        )

    return AgentInput(
        question=str(question or ""),
        messages=[HumanMessage(content=content_blocks or str(question or ""))],
        workspace_id=workspace_id,
        user_id=user_id,
        table_names=normalized_table_names,
        data_path=data_path or None,
        scratchpad_path=scratchpad_path or None,
        run_id=str(run_id or uuid.uuid4()),
        system_info=default_system_info(),
        context=str(context or ""),
        workspace_schema=workspace_schema if isinstance(workspace_schema, dict) else {},
        schema_folder_path=str(schema_folder_path or ""),
        previous_code=str(current_code or ""),
        current_code=str(current_code or ""),
        known_columns=normalized_known_columns,
        attachments=normalized_attachments,
    )
