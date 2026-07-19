"""Prompt + invocation helpers for the reusable coding subagent."""

from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Any, Awaitable, Callable

from langchain_core.messages import AIMessage, AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .schema import AnalysisOutput

_CODING_PROMPT = (
    Path(__file__).parent / "prompts" / "coding_system.yaml"
).read_text(encoding="utf-8")

StructuredInvoker = Callable[[Any, dict[str, Any]], Any]
AsyncStructuredInvoker = Callable[[Any, dict[str, Any]], Awaitable[Any]]


class StructuredOutputEmptyError(ValueError):
    """Raised when structured parsing produces no usable payload."""


def _build_coding_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", _CODING_PROMPT),
            (
                "system",
                (
                    "Workspace database path: {workspace_db_path}\n"
                    "Preferred table: {table_name}\n"
                    "Workspace tables: {workspace_tables_json}\n"
                    "Schema summary (column names only): {schema_summary}\n"
                    "Known columns: {known_columns_json}\n"
                    "Sample table: {sample_table}\n"
                    "Sample rows: {sample_json}\n"
                    "Context: {context}"
                ),
            ),
            MessagesPlaceholder("messages"),
        ]
    )


def _invoke_structured_chain(chain: Any, payload: dict[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"^Pydantic serializer warnings:",
            category=UserWarning,
        )
        return chain.invoke(payload)


async def _ainvoke_structured_chain(chain: Any, payload: dict[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"^Pydantic serializer warnings:",
            category=UserWarning,
        )
        return await chain.ainvoke(payload)


def build_coding_chain(*, model: Any, method: str | None = None) -> Any:
    prompt = _build_coding_prompt()
    if method is None:
        try:
            return prompt | model.with_structured_output(AnalysisOutput, include_raw=True)
        except TypeError:
            return prompt | model.with_structured_output(AnalysisOutput)
    try:
        return prompt | model.with_structured_output(AnalysisOutput, method=method, include_raw=True)
    except TypeError:
        # Test doubles may not accept provider-specific kwargs.
        return prompt | model.with_structured_output(AnalysisOutput)


def build_coding_tool_call_chain(*, model: Any) -> Any:
    prompt = _build_coding_prompt()
    tool_name = str(AnalysisOutput.model_config.get("title") or AnalysisOutput.__name__)
    try:
        return prompt | model.bind_tools([AnalysisOutput], tool_choice=tool_name)
    except TypeError:
        # Some model wrappers may not support tool_choice.
        return prompt | model.bind_tools([AnalysisOutput])


def _build_payload(
    *,
    messages: list[AnyMessage],
    table_name: str,
    workspace_tables_json: str,
    workspace_db_path: str,
    schema_summary: str,
    known_columns_json: str,
    sample_table: str,
    sample_json: str,
    context: str,
) -> dict[str, Any]:
    return {
        "messages": list(messages),
        "table_name": str(table_name or ""),
        "workspace_tables_json": str(workspace_tables_json or ""),
        "workspace_db_path": str(workspace_db_path or ""),
        "schema_summary": str(schema_summary or ""),
        "known_columns_json": str(known_columns_json or ""),
        "sample_table": str(sample_table or ""),
        "sample_json": str(sample_json or ""),
        "context": str(context or ""),
    }


def _validate_analysis_output(output: Any) -> AnalysisOutput:
    if isinstance(output, dict) and output.get("parsed") is not None:
        output = output.get("parsed")
    if output is None:
        raise StructuredOutputEmptyError(
            "Structured output parser returned no data (parsed output is None)."
        )
    if isinstance(output, AnalysisOutput):
        return output
    return AnalysisOutput.model_validate(output)


def _extract_tool_calls(raw_output: Any) -> list[dict[str, Any]]:
    if isinstance(raw_output, dict):
        nested_raw = raw_output.get("raw")
        if nested_raw is not None:
            raw_output = nested_raw
    tool_calls = None
    if isinstance(raw_output, AIMessage):
        tool_calls = raw_output.tool_calls
    elif isinstance(raw_output, dict):
        tool_calls = raw_output.get("tool_calls")
    else:
        tool_calls = getattr(raw_output, "tool_calls", None)
    if not isinstance(tool_calls, list):
        return []
    return [dict(item) for item in tool_calls if isinstance(item, dict)]


def _extract_analysis_args_from_tool_calls(tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    if not tool_calls:
        raise StructuredOutputEmptyError(
            "Structured output returned no tool call arguments."
        )
    tool_name = str(AnalysisOutput.model_config.get("title") or AnalysisOutput.__name__)
    selected_call = None
    for call in tool_calls:
        call_name = str(call.get("name") or call.get("type") or "").strip()
        if call_name == tool_name:
            selected_call = call
            break
    if selected_call is None:
        selected_call = tool_calls[0]
    args = selected_call.get("args")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception as exc:
            raise ValueError("Tool call arguments were not valid JSON.") from exc
    if not isinstance(args, dict):
        raise ValueError("Tool call arguments must be a JSON object.")
    return args


def invoke_coding_chain(
    *,
    chain: Any,
    messages: list[AnyMessage],
    table_name: str,
    workspace_tables_json: str,
    workspace_db_path: str,
    schema_summary: str,
    known_columns_json: str,
    sample_table: str,
    sample_json: str,
    context: str,
    invoke_structured_chain: StructuredInvoker | None = None,
) -> AnalysisOutput:
    invoker = invoke_structured_chain or _invoke_structured_chain
    payload = _build_payload(
        messages=messages,
        table_name=table_name,
        workspace_tables_json=workspace_tables_json,
        workspace_db_path=workspace_db_path,
        schema_summary=schema_summary,
        known_columns_json=known_columns_json,
        sample_table=sample_table,
        sample_json=sample_json,
        context=context,
    )
    output = invoker(chain, payload)
    return _validate_analysis_output(output)


async def ainvoke_coding_chain(
    *,
    chain: Any,
    messages: list[AnyMessage],
    table_name: str,
    workspace_tables_json: str,
    workspace_db_path: str,
    schema_summary: str,
    known_columns_json: str,
    sample_table: str,
    sample_json: str,
    context: str,
    invoke_structured_chain: AsyncStructuredInvoker | None = None,
) -> AnalysisOutput:
    invoker = invoke_structured_chain or _ainvoke_structured_chain
    payload = _build_payload(
        messages=messages,
        table_name=table_name,
        workspace_tables_json=workspace_tables_json,
        workspace_db_path=workspace_db_path,
        schema_summary=schema_summary,
        known_columns_json=known_columns_json,
        sample_table=sample_table,
        sample_json=sample_json,
        context=context,
    )
    output = await invoker(chain, payload)
    return _validate_analysis_output(output)


async def ainvoke_coding_tool_call_chain(
    *,
    chain: Any,
    messages: list[AnyMessage],
    table_name: str,
    workspace_tables_json: str,
    workspace_db_path: str,
    schema_summary: str,
    known_columns_json: str,
    sample_table: str,
    sample_json: str,
    context: str,
    invoke_structured_chain: AsyncStructuredInvoker | None = None,
) -> AnalysisOutput:
    invoker = invoke_structured_chain or _ainvoke_structured_chain
    payload = _build_payload(
        messages=messages,
        table_name=table_name,
        workspace_tables_json=workspace_tables_json,
        workspace_db_path=workspace_db_path,
        schema_summary=schema_summary,
        known_columns_json=known_columns_json,
        sample_table=sample_table,
        sample_json=sample_json,
        context=context,
    )
    raw_output = await invoker(chain, payload)
    tool_calls = _extract_tool_calls(raw_output)
    args = _extract_analysis_args_from_tool_calls(tool_calls)
    return _validate_analysis_output(args)
