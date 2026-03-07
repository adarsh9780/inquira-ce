"""Graph nodes for agent v2."""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from ..agent.code_guard import guard_code
from ..agent.registry import load_agent_runtime_config
from ..services.chat_model_factory import create_chat_model
from ..services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from .router import decide_route
from .streaming import emit_stream_token
from .tools.bash_tool import run_bash
from .tools.execute_python import execute_python
from .tools.finish_analysis import finish_analysis
from .tools.pip_install import pip_install
from .tools.sample_data import sample_data
from .tools.search_schema import search_schema

_ANALYSIS_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "react_system.yaml"
).read_text(encoding="utf-8")
_GENERAL_CHAT_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "general_chat_system.yaml"
).read_text(encoding="utf-8")


class AnalysisOutput(BaseModel):
    code: str | None = None
    explanation: str | None = None
    output_contract: list[dict[str, str]] = Field(default_factory=list)
    search_schema_queries: list[str] = Field(default_factory=list)


class ChatOutput(BaseModel):
    answer: str | None = None


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_stringify_content(item) for item in content if _stringify_content(item))
    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text") or "")
        return json.dumps(content, ensure_ascii=True, default=str)
    return str(content)


def _safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)


def _latest_user_text(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        msg_type = str(getattr(msg, "type", "") or "").lower()
        if msg_type in {"human", "user"}:
            return _stringify_content(getattr(msg, "content", "")).strip()
    if messages:
        return _stringify_content(getattr(messages[-1], "content", "")).strip()
    return ""


def _get_model(config: RunnableConfig, *, lite: bool) -> BaseChatModel:
    runtime = load_llm_runtime_config()
    configurable = config.get("configurable", {})
    selected = normalize_model_id(str(configurable.get("model") or "").strip())
    model_name = selected or (runtime.lite_model if lite else runtime.default_model)
    api_key = str(configurable.get("api_key") or "").strip()
    if runtime.requires_api_key and not api_key:
        raise ValueError("API key not configured for agent v2.")

    return create_chat_model(
        provider=runtime.provider,
        model=model_name,
        api_key=api_key,
        base_url=runtime.base_url,
        temperature=0,
        max_tokens=runtime.code_generation_max_tokens,
    )


def _emit_text_chunks(node_name: str, text: str, chunk_size: int = 24) -> None:
    rendered = str(text or "")
    if not rendered:
        return
    size = max(1, int(chunk_size))
    for idx in range(0, len(rendered), size):
        emit_stream_token(node_name, rendered[idx : idx + size])


def _sanitize_output_contract(contract: Any) -> list[dict[str, str]]:
    if not isinstance(contract, list):
        return []
    accepted: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in contract:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        kind = str(item.get("kind") or "").strip().lower()
        if not name or not name.isidentifier() or kind not in {"dataframe", "figure", "scalar"}:
            continue
        dedupe = name.lower()
        if dedupe in seen:
            continue
        seen.add(dedupe)
        accepted.append({"name": name, "kind": kind})
        if len(accepted) >= 8:
            break
    return accepted


def _normalize_search_queries(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in raw:
        query = str(entry or "").strip()
        if not query:
            continue
        dedupe = query.lower()
        if dedupe in seen:
            continue
        seen.add(dedupe)
        normalized.append(query)
        if len(normalized) >= 3:
            break
    return normalized


def _iter_schema_columns(schema: dict[str, Any], table_name: str | None) -> list[tuple[str, str]]:
    if not isinstance(schema, dict):
        return []
    requested_table = str(table_name or "").strip().lower()
    rows: list[tuple[str, str]] = []

    scoped_table = str(schema.get("table_name") or "").strip()
    scoped_columns = schema.get("columns")
    if isinstance(scoped_columns, list):
        if requested_table and scoped_table and scoped_table.lower() != requested_table:
            return []
        for col in scoped_columns:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name") or "").strip()
            if not name:
                continue
            rows.append((scoped_table, name))
        return rows

    tables = schema.get("tables")
    if not isinstance(tables, list):
        return rows
    for table in tables:
        if not isinstance(table, dict):
            continue
        candidate_table = str(table.get("table_name") or "").strip()
        if requested_table and candidate_table.lower() != requested_table:
            continue
        raw_columns = table.get("columns")
        if not isinstance(raw_columns, list):
            continue
        for col in raw_columns:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name") or "").strip()
            if not name:
                continue
            rows.append((candidate_table, name))
    return rows


def _build_schema_summary(schema: dict[str, Any], table_name: str | None) -> str:
    grouped: dict[str, list[str]] = {}
    for candidate_table, name in _iter_schema_columns(schema, table_name):
        key = candidate_table or (str(table_name or "").strip() or "data_table")
        grouped.setdefault(key, []).append(name)

    if not grouped:
        return "No schema columns available."

    lines: list[str] = []
    for table, columns in grouped.items():
        deduped: list[str] = []
        seen: set[str] = set()
        for col in columns:
            if col.lower() in seen:
                continue
            seen.add(col.lower())
            deduped.append(col)
        lines.append(f"Table: {table} ({len(deduped)} columns): {', '.join(deduped)}")
    return "\n".join(lines)


def _normalize_known_columns(raw: Any, *, max_items: int = 50) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        table = str(item.get("table_name") or "").strip()
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        dedupe = f"{table.lower()}::{name.lower()}"
        if dedupe in seen:
            continue
        seen.add(dedupe)
        normalized.append(
            {
                "table_name": table,
                "name": name,
                "dtype": str(item.get("dtype") or "").strip(),
                "description": str(item.get("description") or "").strip(),
            }
        )
        if len(normalized) >= max_items:
            break
    return normalized


def _merge_known_columns_lru(
    current: list[dict[str, str]],
    discovered: list[dict[str, Any]],
    *,
    max_items: int = 50,
) -> list[dict[str, str]]:
    ordered = _normalize_known_columns(current, max_items=max_items)
    by_key = {
        f"{item.get('table_name', '').lower()}::{item.get('name', '').lower()}": item
        for item in ordered
    }

    for item in discovered:
        if not isinstance(item, dict):
            continue
        table = str(item.get("table_name") or "").strip()
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        key = f"{table.lower()}::{name.lower()}"
        normalized_item = {
            "table_name": table,
            "name": name,
            "dtype": str(item.get("dtype") or "").strip(),
            "description": str(item.get("description") or "").strip(),
        }
        if key in by_key:
            ordered = [entry for entry in ordered if f"{entry.get('table_name', '').lower()}::{entry.get('name', '').lower()}" != key]
        by_key[key] = normalized_item
        ordered.append(normalized_item)
        if len(ordered) > max_items:
            dropped = ordered.pop(0)
            drop_key = f"{dropped.get('table_name', '').lower()}::{dropped.get('name', '').lower()}"
            by_key.pop(drop_key, None)

    return ordered


def route_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    route = decide_route(state.get("messages") or [], config.get("configurable", {}))
    if route == "unsafe":
        metadata = {"is_safe": False, "is_relevant": False}
    elif route == "general_chat":
        metadata = {"is_safe": True, "is_relevant": False}
    else:
        metadata = {"is_safe": True, "is_relevant": True}
    return {"route": route, "metadata": metadata}


def route_to_next(state: dict[str, Any]) -> str:
    route = str(state.get("route") or "").strip().lower()
    if route == "unsafe":
        return "reject"
    if route == "general_chat":
        return "chat"
    return "react_loop"


def _extract_packages_from_prompt(user_text: str) -> list[str]:
    # Simple parse: "install statsmodels scipy"
    if not user_text:
        return []
    lower = user_text.lower()
    if "install" not in lower:
        return []
    captured = re.search(r"\binstall\s+([a-zA-Z0-9._\- ]{2,200})", user_text, flags=re.IGNORECASE)
    if not captured:
        return []
    packages = []
    for token in captured.group(1).split():
        safe = "".join(ch for ch in token if ch.isalnum() or ch in {".", "_", "-"})
        if safe:
            packages.append(safe)
    return packages[:5]


def _invoke_structured_chain(chain: Any, payload: dict[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"^Pydantic serializer warnings:",
            category=UserWarning,
        )
        return chain.invoke(payload)


def _is_non_retriable_execution_error(message: str) -> bool:
    text = str(message or "").strip().lower()
    if not text:
        return False
    non_retriable_markers = (
        "workspace database is missing",
        "missing workspace data path",
        "missing data path",
        "requires workspace_id",
        "requires workspace_duckdb_path",
        "api key not configured",
    )
    return any(marker in text for marker in non_retriable_markers)


async def react_loop_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    messages = list(state.get("messages") or [])
    table_name = str(state.get("table_name") or "")
    data_path = str(state.get("data_path") or "")
    schema = state.get("active_schema") if isinstance(state.get("active_schema"), dict) else {}
    workspace_id = str(state.get("workspace_id") or "")
    user_id = str(state.get("user_id") or "")
    user_text = _latest_user_text(messages)
    runtime = load_agent_runtime_config()
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)

    schema_summary = _build_schema_summary(schema=schema, table_name=table_name or None)
    sample = sample_data(data_path=data_path or None, table_name=table_name or None, limit=5)

    requested_packages = _extract_packages_from_prompt(user_text)
    if requested_packages:
        await pip_install(
            user_id=user_id,
            workspace_id=workspace_id,
            data_path=data_path or None,
            packages=requested_packages,
        )

    if user_text.startswith("!bash "):
        command = user_text[6:].strip()
        if command:
            await run_bash(
                user_id=user_id,
                workspace_id=workspace_id,
                data_path=data_path or None,
                command=command,
                timeout=60,
            )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _ANALYSIS_PROMPT),
            (
                "system",
                (
                    "Workspace database path: {workspace_db_path}\n"
                    "Table: {table_name}\n"
                    "Schema summary (column names only): {schema_summary}\n"
                    "Known columns: {known_columns_json}\n"
                    "Sample rows: {sample_json}\n"
                    "Context: {context}"
                ),
            ),
            MessagesPlaceholder("messages"),
        ]
    )
    model = _get_model(config, lite=False)
    chain = prompt | model.with_structured_output(AnalysisOutput)

    retry_feedback = ""
    best_output = AnalysisOutput(code="", explanation="", output_contract=[])
    max_attempts = max(1, int(runtime.max_code_executions))
    max_schema_search_calls = max(1, int(runtime.max_tool_calls))
    total_iterations = max_attempts + max_schema_search_calls
    search_calls = 0
    searched_schema_queries: set[str] = set()
    execution_attempts = 0
    candidate_code = ""
    execution_feedback = ""
    last_executed_code = ""
    for _attempt in range(total_iterations):
        call_messages = list(messages)
        if retry_feedback:
            call_messages.append(
                HumanMessage(
                    content=(
                        "Regenerate safer and executable code.\n"
                        f"Previous issue: {retry_feedback}"
                    )
                )
            )

        output = _invoke_structured_chain(
            chain,
            {
                "messages": call_messages,
                "table_name": table_name or "data_table",
                "workspace_db_path": data_path or "",
                "schema_summary": schema_summary,
                "known_columns_json": _safe_json_dumps(known_columns),
                "sample_json": _safe_json_dumps(sample),
                "context": str(state.get("context") or ""),
            },
        )
        if isinstance(output, AnalysisOutput):
            best_output = output
        else:
            best_output = AnalysisOutput.model_validate(output)

        search_queries = _normalize_search_queries(best_output.search_schema_queries)
        pending_search_queries = [
            query
            for query in search_queries
            if query.lower() not in searched_schema_queries
        ]
        if pending_search_queries and search_calls < max_schema_search_calls:
            for query in pending_search_queries:
                if search_calls >= max_schema_search_calls:
                    break
                searched_schema_queries.add(query.lower())
                search_calls += 1
                search_result = search_schema(
                    schema=schema,
                    query=query,
                    table_name=table_name or None,
                    max_results=20,
                )
                discovered = search_result.get("columns") if isinstance(search_result, dict) else []
                if isinstance(discovered, list):
                    known_columns = _merge_known_columns_lru(
                        known_columns,
                        discovered,
                        max_items=50,
                    )
            retry_feedback = (
                "Additional schema details were retrieved with search_schema. "
                "Use known columns to generate executable Python code."
            )
            candidate_code = ""
            continue

        candidate_code = str(best_output.code or "").strip()
        if not candidate_code:
            retry_feedback = "No code was produced. Generate executable Python code."
            continue

        guard = guard_code(candidate_code, table_name=table_name or None)
        if not guard.blocked:
            candidate_code = guard.code
        else:
            retry_feedback = str(guard.reason or "Generated code failed validation.")
            candidate_code = ""
            continue

        execution_attempts += 1
        execution = await execute_python(
            workspace_id=workspace_id,
            data_path=data_path or None,
            code=candidate_code,
            timeout=min(90, max(10, int(runtime.turn_timeout))),
        )
        last_executed_code = candidate_code
        if bool(execution.get("success")):
            execution_feedback = ""
            retry_feedback = ""
            break

        execution_feedback = str(execution.get("error") or execution.get("stderr") or "").strip()
        if _is_non_retriable_execution_error(execution_feedback):
            break
        if execution_attempts >= max_attempts:
            break
        retry_feedback = (
            "Execution failed. Regenerate code that fixes this runtime error.\n"
            f"Runtime error: {execution_feedback[:1200]}"
        )
        candidate_code = ""
    if not candidate_code and execution_feedback:
        candidate_code = last_executed_code

    explanation = str(best_output.explanation or "").strip()
    if execution_feedback:
        explanation = (
            f"{explanation}\n\nExecution warning: {execution_feedback}"
            if explanation
            else f"Execution warning: {execution_feedback}"
        )
    if retry_feedback and not candidate_code:
        explanation = (
            f"{explanation}\n\nI could not produce safe executable code.\nReason: {retry_feedback}"
            if explanation
            else f"I could not produce safe executable code.\nReason: {retry_feedback}"
        )
    if not explanation:
        explanation = "Analysis completed. Review the generated code and output."

    _emit_text_chunks("finalize", explanation)
    return {
        "route": "analysis",
        "final_code": candidate_code or "",
        "final_explanation": explanation,
        "output_contract": _sanitize_output_contract(best_output.output_contract),
        "metadata": {"is_safe": True, "is_relevant": True},
        "messages": [AIMessage(content=explanation)],
        "last_error": retry_feedback or execution_feedback,
        "known_columns": known_columns,
    }


def chat_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _GENERAL_CHAT_PROMPT),
            MessagesPlaceholder("messages"),
        ]
    )
    model = _get_model(config, lite=True)
    chain = prompt | model.with_structured_output(ChatOutput)
    output = _invoke_structured_chain(chain, {"messages": list(state.get("messages") or [])})
    if isinstance(output, ChatOutput):
        text = str(output.answer or "").strip()
    else:
        text = str(getattr(output, "answer", "") or "").strip()
    if not text:
        text = "I can help you analyze your dataset. Tell me what insight you want."
    _emit_text_chunks("chat", text)
    return {
        "route": "general_chat",
        "final_code": "",
        "final_explanation": text,
        "output_contract": [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "metadata": {"is_safe": True, "is_relevant": False},
        "messages": [AIMessage(content=text)],
    }


def reject_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    text = (
        "I can’t help with that request because it could be unsafe. "
        "I can still help with safe data analysis tasks in your workspace."
    )
    _emit_text_chunks("reject", text)
    return {
        "route": "unsafe",
        "final_code": "",
        "final_explanation": text,
        "output_contract": [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "metadata": {"is_safe": False, "is_relevant": False},
        "messages": [AIMessage(content=text)],
    }


def _strip_scratchpad_references(text: str, scratchpad_path: str | None) -> str:
    rendered = str(text or "")
    if not rendered:
        return rendered
    needle = str(scratchpad_path or "").strip()
    if not needle:
        return rendered
    lines = [line for line in rendered.splitlines() if needle not in line]
    return "\n".join(lines).strip()


def finalize_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    code = _strip_scratchpad_references(
        str(state.get("final_code") or ""),
        state.get("scratchpad_path"),
    )
    explanation = _strip_scratchpad_references(
        str(state.get("final_explanation") or ""),
        state.get("scratchpad_path"),
    )
    if not explanation:
        explanation = "Analysis completed."

    finish = finish_analysis(explanation=explanation, code=code)
    return {
        "final_code": finish.get("final_code", code),
        "final_explanation": finish.get("final_explanation", explanation),
        "messages": [AIMessage(content=finish.get("final_explanation", explanation))],
        "output_contract": state.get("output_contract") or [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "route": state.get("route") or "analysis",
        "metadata": state.get("metadata") or {"is_safe": True, "is_relevant": True},
        "run_id": state.get("run_id"),
    }
