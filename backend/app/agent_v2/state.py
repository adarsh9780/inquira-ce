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
    messages: Annotated[list[AnyMessage], add_messages]
    workspace_id: str
    user_id: str
    table_name: str | None
    data_path: str | None
    scratchpad_path: str | None
    run_id: str
    system_info: SystemInfo
    context: str
    active_schema: dict[str, Any]
    previous_code: str
    current_code: str


class AgentOutput(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    final_code: str | None
    final_explanation: str | None
    output_contract: list[dict[str, str]]
    route: str
    run_id: str
    metadata: dict[str, Any]


class AgentState(AgentInput, total=False):
    route: str
    final_code: str | None
    final_explanation: str | None
    output_contract: list[dict[str, str]]
    metadata: dict[str, Any]
    tool_calls: int
    code_attempts: int
    last_error: str


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
    schema: dict[str, Any],
    current_code: str,
    table_name: str,
    data_path: str,
    context: str,
    workspace_id: str,
    user_id: str,
    scratchpad_path: str,
    run_id: str | None = None,
    **_: Any,
) -> AgentInput:
    return AgentInput(
        messages=[HumanMessage(content=question)],
        workspace_id=workspace_id,
        user_id=user_id,
        table_name=table_name or None,
        data_path=data_path or None,
        scratchpad_path=scratchpad_path or None,
        run_id=str(run_id or uuid.uuid4()),
        system_info=default_system_info(),
        context=str(context or ""),
        active_schema=dict(schema or {}),
        previous_code=str(current_code or ""),
        current_code=str(current_code or ""),
    )
