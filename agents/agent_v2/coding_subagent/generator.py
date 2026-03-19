"""Prompt + invocation helpers for the reusable coding subagent."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Awaitable, Callable

from langchain_core.messages import AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .schema import AnalysisOutput

_CODING_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "coding_system.yaml"
).read_text(encoding="utf-8")

StructuredInvoker = Callable[[Any, dict[str, Any]], Any]
AsyncStructuredInvoker = Callable[[Any, dict[str, Any]], Awaitable[Any]]


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


def build_coding_chain(*, model: Any) -> Any:
    prompt = ChatPromptTemplate.from_messages(
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
    return prompt | model.with_structured_output(AnalysisOutput)


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
    payload = {
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
    output = invoker(chain, payload)
    if isinstance(output, AnalysisOutput):
        return output
    return AnalysisOutput.model_validate(output)


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
    payload = {
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
    output = await invoker(chain, payload)
    if isinstance(output, AnalysisOutput):
        return output
    return AnalysisOutput.model_validate(output)
