"""Graph nodes for agent v2."""

from __future__ import annotations

import asyncio
import ast
import json
import re
import warnings
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from .coding_subagent import AnalysisOutput, ainvoke_coding_chain, build_coding_chain
from .services.chat_model_factory import create_chat_model
from .services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from .services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key
from .code_guard import guard_code
from .events import emit_agent_event
from .router import decide_route
from .runtime import load_agent_runtime_config
from .streaming import emit_stream_token
from .tools.bash_tool import run_bash
from .tools.execute_python import execute_python
from .tools.finish_analysis import finish_analysis
from .tools.pip_install import pip_install
from .tools.sample_data import sample_data
from .tools.search_schema import search_schema
from .tools.validate_result import validate_and_summarize_result

_GENERAL_CHAT_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "general_chat_system.yaml"
).read_text(encoding="utf-8")
_RESULT_EXPLANATION_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "result_explanation_system.yaml"
).read_text(encoding="utf-8")
_ASSESS_CONTEXT_PROMPT = (
    "You decide whether the agent has enough schema/data context to generate executable analysis code.\n"
    "Return strict JSON with fields:\n"
    "- enough_context: boolean\n"
    "- missing_context: string[] (short gaps)\n"
    "- tool_plan: list of tool actions.\n"
    "Allowed tool actions:\n"
    "- {{tool: \"search_schema\", query: string, table_name?: string, limit?: int}}\n"
    "- {{tool: \"sample_data\", table_name?: string, limit?: int}}\n"
    "- {{tool: \"bash\", command: string}}\n"
    "Never emit pip_install. Keep tool_plan empty when enough_context=true."
)


class ChatOutput(BaseModel):
    answer: str | None = None


class ResultExplanation(BaseModel):
    result_explanation: str | None = None
    code_explanation: str | None = None


class AnalysisToolPlanItem(BaseModel):
    tool: str
    query: str | None = None
    table_name: str | None = None
    limit: int | None = None
    command: str | None = None


class AnalysisContextAssessment(BaseModel):
    enough_context: bool = False
    missing_context: list[str] = []
    tool_plan: list[AnalysisToolPlanItem] = []


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


def _bounded_messages(messages: list[AnyMessage], *, max_messages: int = 8) -> list[AnyMessage]:
    if not isinstance(messages, list):
        return []
    safe_max = max(1, int(max_messages))
    return list(messages[-safe_max:])


def _sanitize_tool_plan(raw: Any, *, max_items: int = 5) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    accepted: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip().lower()
        if tool not in {"search_schema", "sample_data", "bash"}:
            continue
        normalized: dict[str, Any] = {"tool": tool}
        if tool == "search_schema":
            query = str(item.get("query") or "").strip()
            if not query:
                continue
            normalized["query"] = query
            if str(item.get("table_name") or "").strip():
                normalized["table_name"] = str(item.get("table_name") or "").strip()
            normalized["limit"] = max(1, min(50, int(item.get("limit") or 20)))
        elif tool == "sample_data":
            if str(item.get("table_name") or "").strip():
                normalized["table_name"] = str(item.get("table_name") or "").strip()
            normalized["limit"] = max(1, min(20, int(item.get("limit") or 5)))
        elif tool == "bash":
            command = str(item.get("command") or "").strip()
            if not command:
                continue
            normalized["command"] = command
        accepted.append(normalized)
        if len(accepted) >= max_items:
            break
    return accepted


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
    coding_model = normalize_model_id(str(configurable.get("coding_model") or "").strip())
    if lite:
        model_name = selected or lite_model or default_model
    else:
        model_name = coding_model or selected or default_model
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


def _extract_search_queries_from_code(code: str) -> list[str]:
    candidate = str(code or "").strip()
    if not candidate:
        return []
    try:
        parsed = ast.parse(candidate)
    except Exception:
        return []

    recovered: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(parsed):
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "search_schema_queries" not in targets:
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            continue
        for element in value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                continue
            query = str(element.value or "").strip()
            if not query:
                continue
            dedupe = query.lower()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            recovered.append(query)
            if len(recovered) >= 3:
                return recovered
    return recovered


def _truncate_line(value: str, *, limit: int = 140) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 3)]}..."


def _build_schema_summary(
    *,
    table_names: list[str],
    workspace_schema: Any,
    known_columns: list[dict[str, str]],
    max_tables: int = 8,
) -> str:
    if not isinstance(workspace_schema, dict):
        if table_names:
            return f"Workspace tables: {', '.join(table_names)}"
        return "No preloaded schema summary. Use search_schema tool to discover relevant columns."

    tables = workspace_schema.get("tables")
    if not isinstance(tables, list):
        if table_names:
            return f"Workspace tables: {', '.join(table_names)}"
        return "No preloaded schema summary. Use search_schema tool to discover relevant columns."

    known_by_table: dict[str, list[str]] = {}
    for col in known_columns:
        if not isinstance(col, dict):
            continue
        table = str(col.get("table_name") or "").strip().lower()
        name = str(col.get("name") or "").strip()
        desc = _truncate_line(str(col.get("description") or ""), limit=120)
        if not name:
            continue
        entry = name if not desc else f"{name}: {desc}"
        known_by_table.setdefault(table, []).append(entry)

    selected_tables: list[dict[str, Any]] = []
    table_filter = {str(item).strip().lower() for item in table_names if str(item).strip()}
    for table in tables:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name") or "").strip()
        if not table_name:
            continue
        if table_filter and table_name.lower() not in table_filter:
            continue
        selected_tables.append(table)
        if len(selected_tables) >= max_tables:
            break

    if not selected_tables:
        return "No preloaded schema summary. Use search_schema tool to discover relevant columns."

    lines: list[str] = []
    for table in selected_tables:
        table_name = str(table.get("table_name") or "").strip()
        table_context = _truncate_line(str(table.get("context") or ""), limit=170)
        if table_context:
            lines.append(f"{table_name}: {table_context}")
        else:
            lines.append(f"{table_name}: table description unavailable.")
        raw_columns = table.get("columns")
        columns = raw_columns if isinstance(raw_columns, list) else []
        column_names = [str(col.get("name") or "").strip() for col in columns if isinstance(col, dict)]
        column_names = [name for name in column_names if name]
        if column_names:
            lines.append(f"Columns: {', '.join(column_names[:10])}")

        described_columns: list[str] = []
        for col in columns:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name") or "").strip()
            desc = _truncate_line(str(col.get("description") or ""), limit=100)
            if not name or not desc:
                continue
            described_columns.append(f"{name}: {desc}")
            if len(described_columns) >= 2:
                break
        if described_columns:
            lines.append(f"Column descriptions: {'; '.join(described_columns)}")

        known_entries = known_by_table.get(table_name.lower(), [])
        if known_entries:
            lines.append(f"Known columns cache: {'; '.join(known_entries[:3])}")

    return "\n".join(lines)


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


def _state_table_names(state: dict[str, Any], *, max_items: int = 8) -> list[str]:
    return _normalize_table_names(state.get("table_names"), max_items=max_items)


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


async def route_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    route = await decide_route(state.get("messages") or [], config.get("configurable", {}))
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
    return "analysis_collect_context"


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


async def _ainvoke_structured_chain(chain: Any, payload: dict[str, Any]) -> Any:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"^Pydantic serializer warnings:",
            category=UserWarning,
        )
        ainvoke = getattr(chain, "ainvoke", None)
        if not callable(ainvoke):
            raise TypeError("Async contract violation: runnable is missing ainvoke().")
        return await ainvoke(payload)


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


def _emit_agent_status(
    *,
    step: str,
    message: str,
    detail: str = "",
    attempt: int | None = None,
    next_action: str = "",
    context: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "step": str(step or "").strip(),
        "message": str(message or "").strip(),
    }
    normalized_detail = str(detail or "").strip()
    if normalized_detail:
        payload["detail"] = normalized_detail
    if attempt is not None:
        payload["attempt"] = int(attempt)
    normalized_next_action = str(next_action or "").strip()
    if normalized_next_action:
        payload["next_action"] = normalized_next_action
    if isinstance(context, dict) and context:
        payload["context"] = context
    emit_agent_event("agent_status", payload)


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
    output = await _ainvoke_structured_chain(
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


async def analysis_collect_context_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    messages = _bounded_messages(list(state.get("messages") or []), max_messages=8)
    table_names = _state_table_names(state, max_items=16)
    data_path = str(state.get("data_path") or "")
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    sample_table = table_names[0] if len(table_names) == 1 else None
    workspace_schema = state.get("workspace_schema") if isinstance(state.get("workspace_schema"), dict) else {}
    schema_summary = _build_schema_summary(
        table_names=table_names,
        workspace_schema=workspace_schema,
        known_columns=known_columns,
    )
    user_text = _latest_user_text(messages)
    runtime = load_agent_runtime_config()
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}

    return {
        "analysis_context": {
            "messages": messages,
            "user_text": user_text,
            "schema_summary": schema_summary,
            "schema_tables": table_names,
            "table_names": table_names,
            "sample_table": sample_table or "",
            "data_path": data_path,
            "context": str(state.get("context") or ""),
            "workspace_schema": workspace_schema,
        },
        "known_columns": known_columns,
        "attempt_counters": {
            "generation": int(attempt_counters.get("generation") or 0),
            "execution": int(attempt_counters.get("execution") or 0),
            "enrichment": int(attempt_counters.get("enrichment") or 0),
            "max_code_executions": max(1, int(runtime.max_code_executions)),
            "max_tool_calls": max(1, int(runtime.max_tool_calls)),
        },
        "enrichment_results": state.get("enrichment_results") if isinstance(state.get("enrichment_results"), dict) else {},
        "retry_feedback": str(state.get("retry_feedback") or ""),
    }


async def analysis_assess_context_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    messages = list(analysis_context.get("messages") or [])
    user_text = str(analysis_context.get("user_text") or "")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _ASSESS_CONTEXT_PROMPT),
            (
                "human",
                (
                    "User question: {user_text}\n\n"
                    "Schema summary:\n{schema_summary}\n\n"
                    "Known columns: {known_columns_json}\n\n"
                    "Prior retry feedback: {retry_feedback}\n\n"
                    "Messages window size: {message_count}"
                ),
            ),
        ]
    )
    model = _get_model(config, lite=True)
    chain = prompt | model.with_structured_output(AnalysisContextAssessment)
    output = await _ainvoke_structured_chain(
        chain,
        {
            "user_text": user_text,
            "schema_summary": str(analysis_context.get("schema_summary") or ""),
            "known_columns_json": _safe_json_dumps(state.get("known_columns") or []),
            "retry_feedback": str(state.get("retry_feedback") or ""),
            "message_count": len(messages),
        },
    )
    if isinstance(output, AnalysisContextAssessment):
        assessed = output
    else:
        assessed = AnalysisContextAssessment.model_validate(output)

    tool_plan = _sanitize_tool_plan([item.model_dump() for item in assessed.tool_plan], max_items=5)
    return {
        "context_sufficiency": {
            "enough_context": bool(assessed.enough_context),
            "missing_context": [str(item).strip() for item in (assessed.missing_context or []) if str(item).strip()][:6],
        },
        "tool_plan": tool_plan,
    }


def analysis_assess_to_next(state: dict[str, Any]) -> str:
    sufficiency = state.get("context_sufficiency") if isinstance(state.get("context_sufficiency"), dict) else {}
    enough_context = bool(sufficiency.get("enough_context"))
    tool_plan = state.get("tool_plan") if isinstance(state.get("tool_plan"), list) else []
    if enough_context or not tool_plan:
        return "analysis_generate_code"
    return "analysis_enrich_context"


async def analysis_enrich_context_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    tool_plan = state.get("tool_plan") if isinstance(state.get("tool_plan"), list) else []
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    max_tool_calls = max(1, int(attempt_counters.get("max_tool_calls") or 5))
    enrichment_count = int(attempt_counters.get("enrichment") or 0)
    performed = 0
    enrichment_results: dict[str, Any] = {}

    for action in tool_plan:
        if not isinstance(action, dict):
            continue
        if performed >= max_tool_calls:
            break
        tool = str(action.get("tool") or "").strip().lower()
        if tool == "search_schema":
            query = str(action.get("query") or "").strip()
            if not query:
                continue
            _emit_agent_status(
                step="searching_schema",
                message=f"Searching schema for \"{query}\"...",
                detail="Finding relevant columns before code generation.",
                next_action="Use found schema columns in next code generation attempt.",
            )
            result = await asyncio.to_thread(
                search_schema,
                schema=analysis_context.get("workspace_schema") if isinstance(analysis_context.get("workspace_schema"), dict) else {},
                data_path=str(analysis_context.get("data_path") or "") or None,
                table_names=_normalize_table_names(analysis_context.get("table_names"), max_items=64),
                query=query,
                table_name=str(action.get("table_name") or "").strip() or None,
                max_results=int(action.get("limit") or 20),
            )
            if int(result.get("match_count") or 0) == 0:
                for keyword in _normalize_search_queries(re.split(r"[\s,;:/|]+", query)):
                    token = keyword.strip()
                    if len(token) < 3:
                        continue
                    token_result = await asyncio.to_thread(
                        search_schema,
                        schema=analysis_context.get("workspace_schema")
                        if isinstance(analysis_context.get("workspace_schema"), dict)
                        else {},
                        data_path=str(analysis_context.get("data_path") or "") or None,
                        table_names=_normalize_table_names(analysis_context.get("table_names"), max_items=64),
                        query=token,
                        table_name=str(action.get("table_name") or "").strip() or None,
                        max_results=min(10, int(action.get("limit") or 20)),
                    )
                    token_columns = token_result.get("columns") if isinstance(token_result, dict) else []
                    if isinstance(token_columns, list) and token_columns:
                        merged_columns = result.get("columns") if isinstance(result.get("columns"), list) else []
                        result["columns"] = [*merged_columns, *token_columns]
                        result["match_count"] = len(result["columns"])
                        break
            discovered = result.get("columns") if isinstance(result, dict) else []
            if isinstance(discovered, list):
                known_columns = _merge_known_columns_lru(known_columns, discovered, max_items=50)
            enrichment_results.setdefault("search_schema", []).append(result)
            performed += 1
        elif tool == "sample_data":
            sample = sample_data(
                data_path=str(analysis_context.get("data_path") or "") or None,
                table_name=str(action.get("table_name") or analysis_context.get("sample_table") or "").strip() or None,
                limit=int(action.get("limit") or 5),
            )
            enrichment_results["sample_data"] = sample
            performed += 1
        elif tool == "bash":
            command = str(action.get("command") or "").strip()
            if not command:
                continue
            output = await run_bash(
                user_id=str(state.get("user_id") or ""),
                workspace_id=str(state.get("workspace_id") or ""),
                data_path=str(analysis_context.get("data_path") or "") or None,
                command=command,
                timeout=60,
            )
            enrichment_results.setdefault("bash", []).append(output)
            performed += 1

    return {
        "known_columns": known_columns,
        "enrichment_results": enrichment_results,
        "attempt_counters": {
            **attempt_counters,
            "enrichment": enrichment_count + 1,
        },
        "retry_feedback": "Context enrichment completed. Regenerate executable code using enriched context.",
    }


async def analysis_generate_code_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    messages = list(analysis_context.get("messages") or [])
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    sample_table = str(analysis_context.get("sample_table") or "").strip() or None
    sample = state.get("enrichment_results", {}).get("sample_data") if isinstance(state.get("enrichment_results"), dict) else None
    if not isinstance(sample, list):
        sample = sample_data(
            data_path=str(analysis_context.get("data_path") or "") or None,
            table_name=sample_table,
            limit=5,
        )

    retry_feedback = str(state.get("retry_feedback") or "").strip()
    if retry_feedback:
        messages = list(messages) + [HumanMessage(content=f"Fix the previous issue: {retry_feedback}")]
    table_names = _normalize_table_names(analysis_context.get("table_names"), max_items=16)
    table_hint = table_names[0] if table_names else ""

    _emit_agent_status(
        step="generating_code",
        message="Generating analysis code...",
        detail="Creating executable Python code from available schema and context.",
        next_action="Validate generated code and execute it.",
    )

    model = _get_model(config, lite=False)
    chain = build_coding_chain(model=model)
    output = await ainvoke_coding_chain(
        chain=chain,
        messages=messages,
        table_name=table_hint,
        workspace_tables_json=_safe_json_dumps(table_names),
        workspace_db_path=str(analysis_context.get("data_path") or ""),
        schema_summary=str(analysis_context.get("schema_summary") or ""),
        known_columns_json=_safe_json_dumps(known_columns),
        sample_table=sample_table or "",
        sample_json=_safe_json_dumps(sample),
        context=str(analysis_context.get("context") or ""),
        invoke_structured_chain=_ainvoke_structured_chain,
    )
    candidate_code = str(output.code or "").strip()
    requested_queries = _normalize_search_queries(output.search_schema_queries)
    if not requested_queries:
        requested_queries = _extract_search_queries_from_code(candidate_code)
    if requested_queries:
        attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
        return {
            "analysis_output": output.model_dump(),
            "candidate_code": "",
            "tool_plan": [{"tool": "search_schema", "query": query, "limit": 20} for query in requested_queries],
            "retry_target": "analysis_enrich_context",
            "retry_feedback": (
                "Code generation requested additional schema lookup. "
                "Run search_schema tool calls before the next generation attempt."
            ),
            "attempt_counters": {
                **attempt_counters,
                "generation": int(attempt_counters.get("generation") or 0) + 1,
            },
        }

    sanitized_output_contract = _sanitize_output_contract(output.output_contract)
    selected_tables = _normalize_table_names(output.selected_tables)

    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    return {
        "analysis_output": output.model_dump(),
        "candidate_code": candidate_code,
        "retry_target": "",
        "output_contract": sanitized_output_contract,
        "metadata": {
            "is_safe": True,
            "is_relevant": True,
            "tables_used": selected_tables or ([table_hint] if table_hint else []),
            "joins_used": bool(output.joins_used),
            "join_keys": [str(item).strip() for item in (output.join_keys or []) if str(item).strip()][:8],
            "sample_table": str(sample_table or ""),
        },
        "attempt_counters": {
            **attempt_counters,
            "generation": int(attempt_counters.get("generation") or 0) + 1,
        },
    }


def analysis_generate_to_next(state: dict[str, Any]) -> str:
    if str(state.get("retry_target") or "").strip() == "analysis_enrich_context":
        return "analysis_enrich_context"
    code = str(state.get("candidate_code") or "").strip()
    if not code:
        return "analysis_retry_decider"
    return "analysis_guard_code"


async def analysis_guard_code_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    code = str(state.get("candidate_code") or "").strip()
    table_names = _state_table_names(state, max_items=16)
    table_name = table_names[0] if table_names else None
    if not code:
        return {
            "guard_result": {"blocked": True, "reason": "No code was produced."},
            "retry_feedback": "No code was produced. Generate executable Python code.",
        }
    guard = guard_code(code, table_name=table_name)
    if guard.blocked:
        reason = str(guard.reason or "Generated code failed validation.")
        _emit_agent_status(
            step="code_validation_failed",
            message="Code validation failed. Regenerating...",
            detail=f"Reason: {_truncate_text(reason, limit=260)}",
            next_action="Generate safer executable code.",
        )
        return {
            "guard_result": {"blocked": True, "reason": reason},
            "retry_feedback": reason,
        }
    return {
        "candidate_code": str(guard.code or "").strip(),
        "guard_result": {"blocked": False, "reason": ""},
    }


def analysis_guard_to_next(state: dict[str, Any]) -> str:
    guard_result = state.get("guard_result") if isinstance(state.get("guard_result"), dict) else {}
    if bool(guard_result.get("blocked")):
        return "analysis_retry_decider"
    return "analysis_execute_code"


async def analysis_execute_code_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    code = str(state.get("candidate_code") or "").strip()
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    execution_attempts = int(attempt_counters.get("execution") or 0) + 1
    runtime = load_agent_runtime_config()
    timeout = min(90, max(10, int(runtime.turn_timeout)))
    _emit_agent_status(
        step="executing_code",
        message="Running code...",
        detail=f"Executing generated Python in workspace runtime (timeout: {timeout}s).",
        attempt=execution_attempts,
        next_action="Use runtime output to decide retry or finalization.",
    )
    execution = await execute_python(
        workspace_id=str(state.get("workspace_id") or ""),
        data_path=str(analysis_context.get("data_path") or "") or None,
        code=code,
        timeout=timeout,
        emit_tool_events=False,
    )
    return {
        "execution_result": execution,
        "final_executed_code": code,
        "attempt_counters": {
            **attempt_counters,
            "execution": execution_attempts,
        },
    }


def analysis_execute_to_next(state: dict[str, Any]) -> str:
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    if bool(execution.get("success")):
        return "analysis_validate_result"
    return "analysis_retry_decider"


async def analysis_retry_decider_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    max_attempts = max(1, int(attempt_counters.get("max_code_executions") or 3))
    execution_attempts = int(attempt_counters.get("execution") or 0)
    generation_attempts = int(attempt_counters.get("generation") or 0)

    guard_result = state.get("guard_result") if isinstance(state.get("guard_result"), dict) else {}
    if bool(guard_result.get("blocked")):
        return {
            "retry_feedback": str(guard_result.get("reason") or "Generated code failed validation."),
            "retry_target": "analysis_generate_code",
        }

    candidate_code = str(state.get("candidate_code") or "").strip()
    if not candidate_code:
        if generation_attempts >= max_attempts:
            return {
                "retry_feedback": "No code was produced after retry limit.",
                "retry_target": "analysis_finalize_failure",
            }
        return {
            "retry_feedback": "No code was produced. Generate executable Python code.",
            "retry_target": "analysis_generate_code",
        }

    error_text = str(execution.get("error") or execution.get("stderr") or "").strip()
    if not error_text:
        return {
            "retry_feedback": "Execution did not return output.",
            "retry_target": "analysis_finalize_failure",
        }
    if _is_non_retriable_execution_error(error_text):
        return {
            "retry_feedback": error_text,
            "retry_target": "analysis_finalize_failure",
        }
    if execution_attempts >= max_attempts:
        return {
            "retry_feedback": error_text,
            "retry_target": "analysis_finalize_failure",
        }

    lowered = error_text.lower()
    if any(token in lowered for token in ["column", "table", "schema", "not found"]):
        return {
            "retry_feedback": f"Execution failed due to missing schema context: {error_text[:1200]}",
            "retry_target": "analysis_enrich_context",
        }
    return {
        "retry_feedback": f"Execution failed. Regenerate code that fixes this runtime error: {error_text[:1200]}",
        "retry_target": "analysis_generate_code",
    }


def analysis_retry_to_next(state: dict[str, Any]) -> str:
    target = str(state.get("retry_target") or "").strip()
    if target == "analysis_enrich_context":
        return "analysis_enrich_context"
    if target == "analysis_generate_code":
        return "analysis_generate_code"
    return "analysis_finalize_failure"


async def analysis_validate_result_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    artifacts = [item for item in (execution.get("artifacts") or []) if isinstance(item, dict)]
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    code = str(state.get("candidate_code") or "").strip()
    analysis_output = state.get("analysis_output") if isinstance(state.get("analysis_output"), dict) else {}
    code_explanation = str(analysis_output.get("explanation") or "").strip()
    _emit_agent_status(
        step="analyzing_results",
        message="Analyzing results...",
        detail="Summarizing runtime output and preparing final user-facing findings.",
        next_action="Generate final explanation.",
    )
    result_summary = await validate_and_summarize_result(
        workspace_id=str(state.get("workspace_id") or ""),
        run_id=str(state.get("run_id") or ""),
        execution_result=execution,
    )
    result_explanation = ""
    try:
        explained = await _generate_result_explanations(
            question=str(analysis_context.get("user_text") or ""),
            code=code,
            code_explanation=code_explanation,
            result_summary=result_summary,
            config=config,
        )
        result_explanation = str(explained.result_explanation or "").strip()
        code_explanation = str(explained.code_explanation or code_explanation).strip()
    except Exception:
        result_explanation = ""

    if not result_explanation:
        stdout = str(execution.get("stdout") or "").strip()
        if stdout:
            result_explanation = stdout[:1200]
        elif code_explanation:
            result_explanation = code_explanation
        else:
            result_explanation = "Analysis completed successfully."

    return {
        "final_execution": execution,
        "final_artifacts": artifacts,
        "result_summary": result_summary,
        "result_explanation": result_explanation,
        "code_explanation": code_explanation,
    }


async def analysis_finalize_success_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    result_explanation = str(state.get("result_explanation") or "").strip() or "Analysis completed."
    _emit_text_chunks("finalize", result_explanation)
    return {
        "route": "analysis",
        "final_code": str(state.get("candidate_code") or ""),
        "final_explanation": result_explanation,
        "result_explanation": result_explanation,
        "code_explanation": str(state.get("code_explanation") or ""),
        "final_execution": state.get("final_execution"),
        "final_artifacts": state.get("final_artifacts") or [],
        "final_executed_code": str(state.get("final_executed_code") or state.get("candidate_code") or ""),
        "output_contract": _sanitize_output_contract(state.get("output_contract") or []),
        "metadata": state.get("metadata") or {"is_safe": True, "is_relevant": True},
        "messages": [AIMessage(content=result_explanation)],
        "last_error": "",
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "run_id": str(state.get("run_id") or ""),
    }


async def analysis_finalize_failure_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    retry_feedback = str(state.get("retry_feedback") or "").strip()
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    runtime_error = str(execution.get("error") or execution.get("stderr") or "").strip()
    if runtime_error:
        result_explanation = (
            "I ran the analysis but could not complete it successfully. "
            f"The last runtime error was: {runtime_error}"
        )
    elif retry_feedback:
        result_explanation = (
            "I could not produce safe executable code for this request. "
            f"Reason: {retry_feedback}"
        )
    else:
        result_explanation = "I could not complete this analysis."
    _emit_text_chunks("finalize", result_explanation)
    return {
        "route": "analysis",
        "final_code": str(state.get("candidate_code") or ""),
        "final_explanation": result_explanation,
        "result_explanation": result_explanation,
        "code_explanation": str(state.get("code_explanation") or ""),
        "final_execution": None,
        "final_artifacts": [],
        "final_executed_code": str(state.get("final_executed_code") or ""),
        "output_contract": _sanitize_output_contract(state.get("output_contract") or []),
        "metadata": state.get("metadata") or {"is_safe": True, "is_relevant": True},
        "messages": [AIMessage(content=result_explanation)],
        "last_error": retry_feedback or runtime_error,
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "run_id": str(state.get("run_id") or ""),
    }


async def react_loop_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    messages = list(state.get("messages") or [])
    table_names = _state_table_names(state, max_items=16)
    data_path = str(state.get("data_path") or "")
    workspace_id = str(state.get("workspace_id") or "")
    user_id = str(state.get("user_id") or "")
    user_text = _latest_user_text(messages)
    runtime = load_agent_runtime_config()
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)

    table_hint = table_names[0] if table_names else None
    schema_summary = "No preloaded schema summary. Use search_schema for column discovery."
    sample_table = table_hint if len(table_names) == 1 else None
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

    model = _get_model(config, lite=False)
    chain = build_coding_chain(model=model)

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

        is_regeneration = bool(retry_feedback)
        generation_message = "Generating analysis code..." if not is_regeneration else "Regenerating code..."
        generation_detail = (
            "Drafting initial executable Python code from your question and current schema."
            if not is_regeneration
            else (
                "Updating the previous code draft using failure feedback.\n"
                f"Feedback: {_truncate_text(retry_feedback, limit=320)}"
            )
        )
        _emit_agent_status(
            step="generating_code",
            message=generation_message,
            detail=generation_detail,
            attempt=_attempt + 1,
            next_action="Validate generated code and run it if it passes safety checks.",
        )

        try:
            best_output = await ainvoke_coding_chain(
                chain=chain,
                messages=call_messages,
                table_name=table_hint or "",
                workspace_tables_json=_safe_json_dumps(table_names),
                workspace_db_path=data_path or "",
                schema_summary=schema_summary,
                known_columns_json=_safe_json_dumps(known_columns),
                sample_table=sample_table or "",
                sample_json=_safe_json_dumps(sample),
                context=str(state.get("context") or ""),
                invoke_structured_chain=_ainvoke_structured_chain,
            )
        except Exception as exc:
            import traceback
            import sys
            print(f"DEBUG: Error inside invoke_coding_chain: {exc}", file=sys.stderr)
            if hasattr(exc, "__cause__"):
                print(f"DEBUG: Cause: {exc.__cause__}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise

        search_queries = _normalize_search_queries(best_output.search_schema_queries)
        if not search_queries:
            search_queries = _extract_search_queries_from_code(best_output.code or "")
        pending_search_queries = [
            query
            for query in search_queries
            if query.lower() not in searched_schema_queries
        ]
        if pending_search_queries and search_calls < max_schema_search_calls:
            for query in pending_search_queries:
                if search_calls >= max_schema_search_calls:
                    break
                _emit_agent_status(
                    step="searching_schema",
                    message=f"Searching schema for \"{query}\"...",
                    detail=(
                        f"Looking up columns related to \"{query}\" so generated code can map "
                        "user language to real schema fields."
                    ),
                    next_action="Use matching columns to regenerate executable code.",
                    context={"query": query},
                )
                searched_schema_queries.add(query.lower())
                search_calls += 1
                search_result = search_schema(
                    data_path=data_path or None,
                    table_names=table_names,
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
                    _emit_agent_status(
                        step="schema_search_result",
                        message=f"Found {len(discovered)} schema matches for \"{query}\".",
                        detail=(
                            "These matches were added to known columns so the next code draft can "
                            "use concrete field names."
                        ),
                        next_action="Regenerate code with the updated column context.",
                        context={"query": query, "match_count": len(discovered)},
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

        guard = guard_code(candidate_code, table_name=table_hint)
        if not guard.blocked:
            candidate_code = guard.code
        else:
            _emit_agent_status(
                step="code_validation_failed",
                message="Code validation failed. Regenerating...",
                detail=(
                    "The generated code was blocked by safety/validation rules.\n"
                    f"Reason: {_truncate_text(guard.reason, limit=260) or 'Generated code failed validation.'}"
                ),
                next_action="Generate a safer executable version of the code.",
            )
            retry_feedback = str(guard.reason or "Generated code failed validation.")
            candidate_code = ""
            continue

        execution_attempts += 1
        execution_timeout = min(90, max(10, int(runtime.turn_timeout)))
        _emit_agent_status(
            step="executing_code",
            message="Running code...",
            detail=(
                "Executing the generated Python against the workspace runtime."
                f" (timeout: {execution_timeout}s)"
            ),
            attempt=execution_attempts,
            next_action="Capture runtime output and artifacts to decide if retries are needed.",
        )
        execution = await execute_python(
            workspace_id=workspace_id,
            data_path=data_path or None,
            code=candidate_code,
            timeout=execution_timeout,
            emit_tool_events=False,
        )
        last_executed_code = candidate_code
        final_executed_code = candidate_code
        if bool(execution.get("success")):
            final_execution = execution
            final_artifacts = [
                item for item in (execution.get("artifacts") or []) if isinstance(item, dict)
            ]
            _emit_agent_status(
                step="execution_success",
                message="Code executed successfully.",
                detail=(
                    f"Execution completed successfully and produced {len(final_artifacts)} artifact(s)."
                ),
                next_action="Analyze the results and produce a final explanation.",
                attempt=execution_attempts,
            )
            execution_feedback = ""
            retry_feedback = ""
            break

        execution_feedback = str(execution.get("error") or execution.get("stderr") or "").strip()
        if _is_non_retriable_execution_error(execution_feedback):
            _emit_agent_status(
                step="execution_failed",
                message=f"Execution failed: {execution_feedback[:200]}",
                detail=(
                    "The runtime returned a non-retriable error.\n"
                    f"Error: {_truncate_text(execution_feedback, limit=320)}"
                ),
                next_action="Stop retries and return the failure summary.",
                attempt=execution_attempts,
            )
            break
        if execution_attempts >= max_attempts:
            _emit_agent_status(
                step="execution_failed",
                message=f"Code failed after {execution_attempts} attempts.",
                detail=(
                    "The code kept failing with retriable runtime errors and reached the retry limit.\n"
                    f"Last error: {_truncate_text(execution_feedback, limit=320)}"
                ),
                next_action="Return the final failure details to the user.",
                attempt=execution_attempts,
            )
            break
        _emit_agent_status(
            step="execution_retry",
            message=f"Code execution failed. Retrying (attempt {execution_attempts + 1}/{max_attempts})...",
            detail=(
                "Execution failed with a retriable runtime error, so the next code draft will adapt "
                "to this failure.\n"
                f"Error: {_truncate_text(execution_feedback, limit=320)}"
            ),
            attempt=execution_attempts + 1,
            next_action="Regenerate code using runtime error feedback and execute again.",
        )
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
            _emit_agent_status(
                step="sampling_results",
                message="Sampling result data before explaining the outcome...",
                detail=(
                    "A large dataframe result was detected, so a sample will be analyzed first "
                    "to create a concise explanation."
                ),
                next_action="Validate and summarize sampled execution output.",
            )
        _emit_agent_status(
            step="analyzing_results",
            message="Analyzing results...",
            detail=(
                "Summarizing runtime output and artifacts, then preparing final user-facing findings."
            ),
            next_action="Generate result explanation from execution summary.",
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
            _emit_agent_status(
                step="result_analysis_failed",
                message=f"Result analysis fallback applied after explanation error: {fallback}",
                detail=(
                    "The explanation helper failed, so the agent is using a fallback final message."
                ),
                next_action="Return fallback result explanation.",
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
    if not selected_tables and table_hint:
        selected_tables = [table_hint]

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
            "sample_table": sample_table or "",
        },
        "messages": [AIMessage(content=result_explanation)],
        "last_error": retry_feedback or execution_feedback,
        "known_columns": known_columns,
        "run_id": str(state.get("run_id") or ""),
    }


async def chat_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _GENERAL_CHAT_PROMPT),
            MessagesPlaceholder("messages"),
        ]
    )
    model = _get_model(config, lite=True)
    chain = prompt | model.with_structured_output(ChatOutput)
    output = await _ainvoke_structured_chain(chain, {"messages": list(state.get("messages") or [])})
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
