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
from ..agent.events import emit_agent_event
from ..agent.registry import load_agent_runtime_config
from ..services.chat_model_factory import create_chat_model
from ..services.code_executor import get_workspace_run_exports
from ..services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from ..services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key
from ..services.output_capture import build_run_wrapped_code
from .router import decide_route
from .streaming import emit_stream_token
from .tools.bash_tool import run_bash
from .tools.execute_python import execute_python
from .tools.finish_analysis import finish_analysis
from .tools.pip_install import pip_install
from .tools.sample_data import sample_data
from .tools.search_schema import search_schema
from .tools.validate_result import validate_and_summarize_result

_ANALYSIS_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "react_system.yaml"
).read_text(encoding="utf-8")
_GENERAL_CHAT_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "general_chat_system.yaml"
).read_text(encoding="utf-8")
_RESULT_EXPLANATION_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "result_explanation_system.yaml"
).read_text(encoding="utf-8")


class AnalysisOutput(BaseModel):
    code: str | None = None
    explanation: str | None = None
    output_contract: list[dict[str, str]] = Field(default_factory=list)
    search_schema_queries: list[str] = Field(default_factory=list)
    selected_tables: list[str] = Field(default_factory=list)
    join_keys: list[str] = Field(default_factory=list)
    joins_used: bool = False


class ChatOutput(BaseModel):
    answer: str | None = None


class ResultExplanation(BaseModel):
    result_explanation: str | None = None
    code_explanation: str | None = None


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
    provider = normalize_llm_provider(str(configurable.get("provider") or runtime.provider))
    base_url = str(configurable.get("base_url") or runtime.base_url).strip()
    default_model = normalize_model_id(
        str(configurable.get("default_model") or runtime.default_model).strip()
    )
    lite_model = normalize_model_id(
        str(configurable.get("lite_model") or runtime.lite_model).strip()
    )
    selected = normalize_model_id(str(configurable.get("model") or "").strip())
    model_name = selected or (lite_model if lite else default_model)
    api_key = str(configurable.get("api_key") or "").strip()
    if provider_requires_api_key(provider) and not api_key:
        raise ValueError("API key not configured for agent v2.")

    return create_chat_model(
        provider=provider,
        model=model_name,
        api_key=api_key,
        base_url=base_url,
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


def _normalize_table_names(raw: Any, *, max_items: int = 8) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in raw:
        table_name = str(entry or "").strip()
        if not table_name:
            continue
        dedupe = table_name.lower()
        if dedupe in seen:
            continue
        seen.add(dedupe)
        normalized.append(table_name)
        if len(normalized) >= max_items:
            break
    return normalized


def _extract_schema_table_names(schema: dict[str, Any]) -> list[str]:
    tables = schema.get("tables")
    if isinstance(tables, list):
        return _normalize_table_names(
            [str(item.get("table_name") or "").strip() for item in tables if isinstance(item, dict)]
        )
    scoped = str(schema.get("table_name") or "").strip()
    return [scoped] if scoped else []


def _select_sample_table(schema: dict[str, Any], preferred_table: str | None) -> str | None:
    preferred = str(preferred_table or "").strip()
    if preferred:
        return preferred
    tables = _extract_schema_table_names(schema)
    if len(tables) == 1:
        return tables[0]
    return None


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


def _truncate_text(value: Any, *, limit: int = 2400) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


async def _generate_result_explanations(
    *,
    question: str,
    code: str,
    code_explanation: str,
    result_summary: dict[str, Any],
    config: RunnableConfig,
) -> ResultExplanation:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _RESULT_EXPLANATION_PROMPT),
            (
                "human",
                (
                    "User question:\n{question}\n\n"
                    "Generated code:\n```python\n{code}\n```\n\n"
                    "Existing technical explanation:\n{code_explanation}\n\n"
                    "Execution summary JSON:\n{result_summary_json}"
                ),
            ),
        ]
    )
    model = _get_model(config, lite=True)
    chain = prompt | model.with_structured_output(ResultExplanation)
    output = _invoke_structured_chain(
        chain,
        {
            "question": question,
            "code": code,
            "code_explanation": code_explanation,
            "result_summary_json": _safe_json_dumps(result_summary),
        },
    )
    if isinstance(output, ResultExplanation):
        return output
    return ResultExplanation.model_validate(output)


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

    preferred_table = table_name or None
    schema_summary = _build_schema_summary(schema=schema, table_name=None)
    sample_table = _select_sample_table(schema, preferred_table)
    sample = sample_data(data_path=data_path or None, table_name=sample_table, limit=5)

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
    final_execution: dict[str, Any] | None = None
    final_artifacts: list[dict[str, Any]] = []
    final_executed_code = ""
    sanitized_output_contract: list[dict[str, str]] = []
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

        emit_agent_event("agent_status", {
            "step": "generating_code",
            "message": "Generating analysis code..." if not retry_feedback else "Regenerating code...",
            "attempt": _attempt + 1,
        })

        output = _invoke_structured_chain(
            chain,
            {
                "messages": call_messages,
                "table_name": preferred_table or "",
                "workspace_tables_json": _safe_json_dumps(_extract_schema_table_names(schema)),
                "workspace_db_path": data_path or "",
                "schema_summary": schema_summary,
                "known_columns_json": _safe_json_dumps(known_columns),
                "sample_table": sample_table or "",
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
                emit_agent_event("agent_status", {
                    "step": "searching_schema",
                    "message": f"Searching schema for \"{query}\"...",
                })
                searched_schema_queries.add(query.lower())
                search_calls += 1
                search_result = search_schema(
                    schema=schema,
                    query=query,
                    table_name=None,
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

        sanitized_output_contract = _sanitize_output_contract(best_output.output_contract)

        guard = guard_code(candidate_code, table_name=table_name or None)
        if not guard.blocked:
            candidate_code = guard.code
        else:
            emit_agent_event("agent_status", {
                "step": "code_validation_failed",
                "message": "Code validation failed. Regenerating...",
            })
            retry_feedback = str(guard.reason or "Generated code failed validation.")
            candidate_code = ""
            continue

        execution_attempts += 1
        emit_agent_event("agent_status", {
            "step": "executing_code",
            "message": "Running code...",
            "attempt": execution_attempts,
        })
        wrapped_code = build_run_wrapped_code(
            candidate_code,
            str(state.get("run_id") or ""),
            sanitized_output_contract,
        )
        execution = await execute_python(
            workspace_id=workspace_id,
            data_path=data_path or None,
            code=wrapped_code,
            timeout=min(90, max(10, int(runtime.turn_timeout))),
            emit_tool_events=False,
        )
        last_executed_code = candidate_code
        final_executed_code = wrapped_code
        if bool(execution.get("success")):
            emit_agent_event("agent_status", {
                "step": "execution_success",
                "message": "Code executed successfully.",
            })
            final_execution = execution
            final_artifacts = [
                item for item in (execution.get("artifacts") or []) if isinstance(item, dict)
            ]
            if not final_artifacts:
                try:
                    exports = await get_workspace_run_exports(
                        workspace_id=workspace_id,
                        run_id=str(state.get("run_id") or ""),
                    )
                except Exception:
                    exports = []
                final_artifacts = [item for item in exports if isinstance(item, dict)]
            execution_feedback = ""
            retry_feedback = ""
            break

        execution_feedback = str(execution.get("error") or execution.get("stderr") or "").strip()
        if _is_non_retriable_execution_error(execution_feedback):
            emit_agent_event("agent_status", {
                "step": "execution_failed",
                "message": f"Execution failed: {execution_feedback[:200]}",
            })
            break
        if execution_attempts >= max_attempts:
            emit_agent_event("agent_status", {
                "step": "execution_failed",
                "message": f"Code failed after {execution_attempts} attempts.",
            })
            break
        emit_agent_event("agent_status", {
            "step": "execution_retry",
            "message": f"Code execution failed. Retrying (attempt {execution_attempts + 1}/{max_attempts})...",
        })
        retry_feedback = (
            "Execution failed. Regenerate code that fixes this runtime error.\n"
            f"Runtime error: {execution_feedback[:1200]}"
        )
        candidate_code = ""
    if not candidate_code and execution_feedback:
        candidate_code = last_executed_code

    code_explanation = str(best_output.explanation or "").strip()
    result_explanation = ""
    result_summary: dict[str, Any] = {
        "success": bool(final_execution and final_execution.get("success")),
        "stdout": "",
        "stderr": _truncate_text(execution_feedback, limit=1800),
        "artifact_count": len(final_artifacts),
    }

    if final_execution:
        if final_artifacts and any(
            str(item.get("kind") or "").strip().lower() == "dataframe"
            and int(item.get("row_count") or 0) > 10
            for item in final_artifacts
            if isinstance(item, dict)
        ):
            emit_agent_event(
                "agent_status",
                {
                    "step": "sampling_results",
                    "message": "Sampling result data before explaining the outcome...",
                },
            )
        emit_agent_event(
            "agent_status",
            {"step": "analyzing_results", "message": "Analyzing results..."},
        )
        result_summary = await validate_and_summarize_result(
            workspace_id=workspace_id,
            run_id=str(state.get("run_id") or ""),
            execution_result=final_execution,
        )
        try:
            explained = await _generate_result_explanations(
                question=user_text,
                code=candidate_code,
                code_explanation=code_explanation,
                result_summary=result_summary,
                config=config,
            )
            result_explanation = str(explained.result_explanation or "").strip()
            code_explanation = str(explained.code_explanation or code_explanation).strip()
        except Exception as exc:
            fallback = _truncate_text(exc, limit=200)
            emit_agent_event(
                "agent_status",
                {
                    "step": "result_analysis_failed",
                    "message": f"Result analysis fallback applied after explanation error: {fallback}",
                },
            )
            result_explanation = ""

    if not result_explanation:
        if execution_feedback:
            result_explanation = (
                "I ran the analysis but could not complete it successfully. "
                f"The last runtime error was: {execution_feedback}"
            )
        elif retry_feedback and not candidate_code:
            result_explanation = (
                "I could not produce safe executable code for this request. "
                f"Reason: {retry_feedback}"
            )
        elif code_explanation:
            result_explanation = code_explanation
        else:
            result_explanation = "Analysis completed."

    selected_tables = _normalize_table_names(best_output.selected_tables)
    if not selected_tables and preferred_table:
        selected_tables = [preferred_table]

    _emit_text_chunks("finalize", result_explanation)
    return {
        "route": "analysis",
        "final_code": candidate_code or "",
        "final_explanation": result_explanation,
        "result_explanation": result_explanation,
        "code_explanation": code_explanation,
        "final_execution": final_execution,
        "final_artifacts": final_artifacts,
        "final_executed_code": final_executed_code or "",
        "output_contract": sanitized_output_contract,
        "metadata": {
            "is_safe": True,
            "is_relevant": True,
            "tables_used": selected_tables,
            "joins_used": bool(best_output.joins_used),
            "join_keys": [
                str(item).strip()
                for item in (best_output.join_keys or [])
                if str(item).strip()
            ][:8],
            "preferred_table": preferred_table or "",
            "sample_table": sample_table or "",
        },
        "messages": [AIMessage(content=result_explanation)],
        "last_error": retry_feedback or execution_feedback,
        "known_columns": known_columns,
        "run_id": str(state.get("run_id") or ""),
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
        "result_explanation": text,
        "code_explanation": "",
        "final_execution": None,
        "final_artifacts": [],
        "final_executed_code": "",
        "output_contract": [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "metadata": {"is_safe": True, "is_relevant": False},
        "messages": [AIMessage(content=text)],
        "run_id": str(state.get("run_id") or ""),
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
        "result_explanation": text,
        "code_explanation": "",
        "final_execution": None,
        "final_artifacts": [],
        "final_executed_code": "",
        "output_contract": [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "metadata": {"is_safe": False, "is_relevant": False},
        "messages": [AIMessage(content=text)],
        "run_id": str(state.get("run_id") or ""),
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
    result_explanation = _strip_scratchpad_references(
        str(state.get("result_explanation") or state.get("final_explanation") or ""),
        state.get("scratchpad_path"),
    )
    code_explanation = _strip_scratchpad_references(
        str(state.get("code_explanation") or ""),
        state.get("scratchpad_path"),
    )
    if not result_explanation:
        result_explanation = "Analysis completed."

    finish = finish_analysis(explanation=result_explanation, code=code)
    return {
        "final_code": finish.get("final_code", code),
        "final_explanation": finish.get("final_explanation", result_explanation),
        "result_explanation": result_explanation,
        "code_explanation": code_explanation,
        "final_execution": state.get("final_execution"),
        "final_artifacts": state.get("final_artifacts") or [],
        "final_executed_code": state.get("final_executed_code") or "",
        "messages": [AIMessage(content=finish.get("final_explanation", result_explanation))],
        "output_contract": state.get("output_contract") or [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "route": state.get("route") or "analysis",
        "metadata": state.get("metadata") or {"is_safe": True, "is_relevant": True},
        "run_id": state.get("run_id"),
    }
