"""Graph nodes for agent v2."""

from __future__ import annotations

import asyncio
import ast
import json
import re
import warnings
from pathlib import Path
from typing import Annotated, Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, tools_condition
from pydantic import BaseModel

from .coding_subagent import ainvoke_coding_chain, build_coding_chain
from .services.chat_model_factory import create_chat_model
from .services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from .services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key
from .code_guard import guard_code
from .events import emit_agent_event
from .router import decide_route
from .runtime import load_agent_runtime_config
from .streaming import emit_stream_token
from .tools.execute_python import execute_python
from .tools.sample_data import sample_data
from .tools.schema_chunks import scan_schema_chunks
from .tools.search_schema import search_schema
from .tools import new_tool_call_id
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
    "- tool_plan: list of tool actions, each with a very short explanation string.\n"
    "Allowed tool actions:\n"
    "- {{tool: \"search_schema\", query: string, table_name?: string, limit?: int, explanation: string}}\n"
    "- {{tool: \"scan_schema_chunks\", query: string, table_name?: string, limit?: int, explanation: string}}\n"
    "- {{tool: \"sample_data\", table_name?: string, limit?: int, explanation: string}}\n"
    "- {{tool: \"bash\", command: string, explanation: string}}\n"
    "Never emit pip_install. Keep tool_plan empty when enough_context=true.\n"
    "For search_schema and scan_schema_chunks, query must be a single keyword token (no spaces).\n"
    "Start with 1-3 broad keyword queries, then narrow only after seeing matches.\n"
    "If search_schema results are weak, include scan_schema_chunks to inspect schema metadata in chunks."
)
_CONTEXT_ENRICHMENT_TOOL_PROMPT = (
    "You are a schema context-gathering assistant for Python data analysis.\n"
    "Decide whether there is enough schema/data context to generate executable analysis code.\n"
    "If context is insufficient, call one tool at a time to gather missing details.\n"
    "Available tools:\n"
    "- search_schema(query?: string, queries?: string[], table_name?: string, limit?: int, explanation?: string)\n"
    "- scan_schema_chunks(query_terms: string[], table_names?: string[], chunk_size?: int, max_chunks?: int, explanation?: string)\n"
    "- sample_data(table_name?: string, limit?: int, explanation?: string)\n"
    "Rules:\n"
    "- Start with ONE batched search_schema call using queries=[...] containing 3-6 broad single-word keywords.\n"
    "- Keep search keywords as single words (no spaces, no long phrases).\n"
    "- Prefer search_schema first; use scan_schema_chunks only when search_schema matches are weak.\n"
    "- After first results, narrow follow-up queries using: prior search results + user question + known columns + missing context.\n"
    "- Avoid repeating the same tool call with identical arguments.\n"
    "- Include explanation in every tool call as one short sentence saying why this tool is the next step.\n"
    "- Stop tool calls as soon as context is sufficient.\n"
    "When finished, return ONLY valid JSON:\n"
    "{\"enough_context\": boolean, \"missing_context\": string[], \"notes\": string}\n"
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
    explanation: str | None = None


class AnalysisContextAssessment(BaseModel):
    enough_context: bool = False
    missing_context: list[str] = []
    tool_plan: list[AnalysisToolPlanItem] = []


class ContextEnrichmentDecision(BaseModel):
    enough_context: bool = False
    missing_context: list[str] = []
    notes: str = ""


_SCHEMA_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "bar",
    "bars",
    "be",
    "by",
    "column",
    "columns",
    "data",
    "dataset",
    "different",
    "for",
    "from",
    "has",
    "in",
    "into",
    "is",
    "it",
    "names",
    "not",
    "of",
    "or",
    "represent",
    "show",
    "specified",
    "table",
    "tables",
    "that",
    "the",
    "their",
    "them",
    "then",
    "these",
    "this",
    "to",
    "types",
    "user",
    "using",
    "values",
    "which",
    "with",
}


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


def _safe_json_loads(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    try:
        fallback = json.loads(match.group(0))
    except Exception:
        return {}
    return fallback if isinstance(fallback, dict) else {}


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


def _extract_schema_query_keywords(value: Any, *, max_items: int = 6) -> list[str]:
    text = " ".join(str(value or "").strip().lower().split())
    if not text:
        return []

    keywords: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text):
        keyword = str(token or "").strip().lower()
        if not keyword:
            continue
        if keyword in seen:
            continue
        if keyword in _SCHEMA_QUERY_STOPWORDS:
            continue
        if len(keyword) < 2 and keyword != "id":
            continue
        seen.add(keyword)
        keywords.append(keyword)
        if len(keywords) >= max(1, int(max_items)):
            break
    return keywords


def _sanitize_tool_plan(raw: Any, *, max_items: int = 5) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    accepted: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append_action(action: dict[str, Any]) -> None:
        key = _safe_json_dumps(action)
        if key in seen:
            return
        seen.add(key)
        accepted.append(action)

    for item in raw:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "").strip().lower()
        if tool not in {"search_schema", "scan_schema_chunks", "sample_data", "bash"}:
            continue
        if tool in {"search_schema", "scan_schema_chunks"}:
            query = str(item.get("query") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            if not query:
                continue
            keyword_queries = _extract_schema_query_keywords(query, max_items=3)
            if not keyword_queries:
                continue
            if str(item.get("table_name") or "").strip():
                normalized_table_name = str(item.get("table_name") or "").strip()
            else:
                normalized_table_name = ""
            normalized_limit = max(1, min(50, int(item.get("limit") or 20)))
            for keyword in keyword_queries:
                normalized: dict[str, Any] = {
                    "tool": tool,
                    "query": keyword,
                    "limit": normalized_limit,
                }
                if explanation:
                    normalized["explanation"] = explanation
                if normalized_table_name:
                    normalized["table_name"] = normalized_table_name
                _append_action(normalized)
                if len(accepted) >= max_items:
                    break
            if len(accepted) >= max_items:
                break
            continue
        elif tool == "sample_data":
            normalized: dict[str, Any] = {"tool": tool}
            explanation = str(item.get("explanation") or "").strip()
            if str(item.get("table_name") or "").strip():
                normalized["table_name"] = str(item.get("table_name") or "").strip()
            normalized["limit"] = max(1, min(20, int(item.get("limit") or 5)))
            if explanation:
                normalized["explanation"] = explanation
            _append_action(normalized)
        elif tool == "bash":
            normalized = {"tool": tool}
            command = str(item.get("command") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            if not command:
                continue
            normalized["command"] = command
            if explanation:
                normalized["explanation"] = explanation
            _append_action(normalized)
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
        model_name = lite_model or selected or default_model
    else:
        model_name = coding_model or default_model
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
        for query in _extract_schema_query_keywords(entry, max_items=3):
            dedupe = query.lower()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            normalized.append(query)
            if len(normalized) >= 3:
                break
        if len(normalized) >= 3:
            break
    return normalized


def _normalize_broad_search_queries(
    *,
    query: str | None,
    queries: list[str] | None,
    max_items: int = 6,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    candidates: list[str] = []
    if str(query or "").strip():
        candidates.append(str(query or "").strip())
    if isinstance(queries, list):
        candidates.extend(str(item or "").strip() for item in queries if str(item or "").strip())

    for candidate in candidates:
        for keyword in _extract_schema_query_keywords(candidate, max_items=max_items):
            dedupe = keyword.lower()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            normalized.append(keyword)
            if len(normalized) >= max(1, int(max_items)):
                return normalized
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


def _schema_memory_md_path(data_path: str | None) -> Path | None:
    base = str(data_path or "").strip()
    if not base:
        return None
    return Path(base).expanduser().resolve().parent / "context" / "schema_analysis_memory.md"


def _load_schema_memory_markdown(data_path: str | None) -> str:
    path = _schema_memory_md_path(data_path)
    if path is None or not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    if not text:
        return ""
    return text[:12000]


def _write_schema_memory_markdown(
    *,
    data_path: str | None,
    user_text: str,
    known_columns: list[dict[str, str]],
    relevant_tables: list[dict[str, Any]] | None = None,
) -> str:
    path = _schema_memory_md_path(data_path)
    if path is None:
        return ""
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in known_columns:
        if not isinstance(item, dict):
            continue
        table_name = str(item.get("table_name") or "").strip() or "unknown_table"
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        grouped.setdefault(table_name, []).append(
            {
                "name": name,
                "dtype": str(item.get("dtype") or "").strip(),
                "description": _truncate_line(str(item.get("description") or ""), limit=140),
            }
        )

    lines: list[str] = [
        "# Schema Analysis Memory",
        "",
        f"- Question focus: {_truncate_line(user_text, limit=220)}",
        "",
        "## Relevant Tables",
    ]
    for table in relevant_tables or []:
        if not isinstance(table, dict):
            continue
        table_name = str(table.get("table_name") or "").strip()
        if not table_name:
            continue
        context = _truncate_line(str(table.get("context") or ""), limit=200)
        lines.append(f"- {table_name}: {context or 'no table description available'}")
    if not (relevant_tables or []):
        lines.append("- none captured yet")

    lines.extend(["", "## Distilled Columns"])
    if not grouped:
        lines.append("- none captured yet")
    else:
        for table_name, columns in grouped.items():
            lines.append(f"### {table_name}")
            for col in columns[:20]:
                dtype = str(col.get("dtype") or "").strip() or "unknown"
                description = str(col.get("description") or "").strip() or "no description"
                lines.append(f"- `{col.get('name')}` ({dtype}): {description}")
            lines.append("")

    rendered = "\n".join(lines).strip() + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    except Exception:
        return ""
    return str(path)


def _build_schema_search_queries(
    *,
    base_query: str,
    user_text: str,
    missing_context: list[str],
    max_queries: int = 6,
) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()

    def _push_keywords(value: str) -> None:
        for token in _extract_schema_query_keywords(value, max_items=max_queries):
            if token in seen:
                continue
            seen.add(token)
            keywords.append(token)
            if len(keywords) >= max_queries:
                break

    _push_keywords(base_query)
    for item in missing_context:
        if len(keywords) >= max_queries:
            break
        _push_keywords(str(item or ""))
    if len(keywords) < max_queries:
        _push_keywords(user_text)
    return keywords[:max_queries]


def _extract_relevant_tables_from_chunk_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = result.get("relevant_tables") if isinstance(result, dict) else []
    if not isinstance(rows, list):
        return []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        table_name = str(row.get("table_name") or "").strip()
        if not table_name:
            continue
        normalized.append(
            {
                "table_name": table_name,
                "context": str(row.get("context") or "").strip(),
                "score": int(row.get("score") or 0),
            }
        )
        if len(normalized) >= 8:
            break
    return normalized


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


@tool("search_schema")
def search_schema_context_tool(
    query: str = "",
    queries: list[str] | None = None,
    table_name: str = "",
    limit: int = 20,
    explanation: str = "",
    analysis_context: Annotated[dict[str, Any], InjectedState("analysis_context")] = None,
) -> dict[str, Any]:
    """Search schema columns using one query or multiple query patterns."""
    context = analysis_context if isinstance(analysis_context, dict) else {}
    workspace_schema = context.get("workspace_schema") if isinstance(context.get("workspace_schema"), dict) else {}
    table_names = _normalize_table_names(context.get("table_names"), max_items=64)
    normalized_queries = _normalize_broad_search_queries(query=query, queries=queries, max_items=8)
    primary_query = normalized_queries[0] if normalized_queries else str(query or "").strip()
    return search_schema(
        schema=workspace_schema,
        data_path=str(context.get("data_path") or "") or None,
        table_names=table_names,
        query=primary_query,
        queries=normalized_queries,
        table_name=str(table_name or "").strip() or None,
        max_results=max(1, min(50, int(limit or 20))),
        explanation=str(explanation or "").strip(),
        emit_tool_events=True,
    )


@tool("scan_schema_chunks")
def scan_schema_chunks_context_tool(
    query_terms: list[str],
    table_names: list[str] | None = None,
    chunk_size: int = 4,
    max_chunks: int = 12,
    explanation: str = "",
    analysis_context: Annotated[dict[str, Any], InjectedState("analysis_context")] = None,
) -> dict[str, Any]:
    """Scan schema metadata in chunks for relevant tables/columns."""
    context = analysis_context if isinstance(analysis_context, dict) else {}
    workspace_schema = context.get("workspace_schema") if isinstance(context.get("workspace_schema"), dict) else {}
    requested_tables = _normalize_table_names(table_names, max_items=64) if isinstance(table_names, list) else []
    default_tables = _normalize_table_names(context.get("table_names"), max_items=64)
    return scan_schema_chunks(
        schema=workspace_schema,
        query_terms=[str(item or "").strip() for item in (query_terms or []) if str(item or "").strip()],
        table_names=requested_tables or default_tables,
        chunk_size=max(1, min(16, int(chunk_size or 4))),
        max_chunks=max(1, min(40, int(max_chunks or 12))),
        explanation=str(explanation or "").strip(),
        emit_tool_events=True,
    )


@tool("sample_data")
def sample_data_context_tool(
    table_name: str = "",
    limit: int = 5,
    explanation: str = "",
    analysis_context: Annotated[dict[str, Any], InjectedState("analysis_context")] = None,
) -> dict[str, Any]:
    """Sample rows from a table to confirm data shape and value patterns."""
    context = analysis_context if isinstance(analysis_context, dict) else {}
    fallback_table = str(context.get("sample_table") or "").strip()
    return sample_data(
        data_path=str(context.get("data_path") or "") or None,
        table_name=str(table_name or "").strip() or fallback_table or None,
        limit=max(1, min(20, int(limit or 5))),
        explanation=str(explanation or "").strip(),
        emit_tool_events=True,
    )


CONTEXT_ENRICHMENT_TOOLS = [
    search_schema_context_tool,
    scan_schema_chunks_context_tool,
    sample_data_context_tool,
]


@tool("sample_data_runtime")
def sample_data_runtime_tool(
    table_name: str = "",
    limit: int = 5,
    explanation: str = "",
    analysis_context: Annotated[dict[str, Any], InjectedState("analysis_context")] = None,
) -> dict[str, Any]:
    """Sample table data during generation/execution flow."""
    context = analysis_context if isinstance(analysis_context, dict) else {}
    fallback_table = str(context.get("sample_table") or "").strip()
    return sample_data(
        data_path=str(context.get("data_path") or "") or None,
        table_name=str(table_name or "").strip() or fallback_table or None,
        limit=max(1, min(20, int(limit or 5))),
        explanation=str(explanation or "").strip(),
        emit_tool_events=True,
    )


@tool("execute_python_runtime")
async def execute_python_runtime_tool(
    code: str,
    timeout: int = 90,
    explanation: str = "",
    analysis_context: Annotated[dict[str, Any], InjectedState("analysis_context")] = None,
    workspace_id: Annotated[str, InjectedState("workspace_id")] = "",
) -> dict[str, Any]:
    """Execute generated Python code in runtime sandbox."""
    context = analysis_context if isinstance(analysis_context, dict) else {}
    return await execute_python(
        workspace_id=str(workspace_id or ""),
        data_path=str(context.get("data_path") or "") or None,
        code=str(code or ""),
        timeout=max(5, int(timeout or 90)),
        explanation=str(explanation or "").strip(),
        emit_tool_events=True,
    )


@tool("validate_result_runtime")
async def validate_result_runtime_tool(
    execution_result: dict[str, Any],
    max_artifacts: int = 3,
    max_rows: int = 5,
    explanation: str = "",
    workspace_id: Annotated[str, InjectedState("workspace_id")] = "",
    run_id: Annotated[str, InjectedState("run_id")] = "",
) -> dict[str, Any]:
    """Normalize runtime execution result for explanation and routing."""
    call_id = new_tool_call_id("validate_result_runtime")
    emit_agent_event(
        "tool_call",
        {
            "tool": "validate_result_runtime",
            "args": {
                "max_artifacts": max(1, min(10, int(max_artifacts or 3))),
                "max_rows": max(1, min(20, int(max_rows or 5))),
                "explanation": str(explanation or "").strip(),
            },
            "call_id": call_id,
            "explanation": str(explanation or "").strip(),
        },
    )
    result = await validate_and_summarize_result(
        workspace_id=str(workspace_id or ""),
        run_id=str(run_id or ""),
        execution_result=execution_result if isinstance(execution_result, dict) else {},
        max_artifacts=max(1, min(10, int(max_artifacts or 3))),
        max_rows=max(1, min(20, int(max_rows or 5))),
    )
    emit_agent_event(
        "tool_result",
        {"call_id": call_id, "output": result, "status": "success", "duration_ms": 1},
    )
    return result


RUNTIME_FLOW_TOOLS = [
    sample_data_runtime_tool,
    execute_python_runtime_tool,
    validate_result_runtime_tool,
]


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


def _is_empty_json_structured_parse_error(exc: Exception) -> bool:
    message = str(exc or "").strip().lower()
    if not message:
        return False
    markers = (
        "expected value at line 1 column 1",
        "expecting value: line 1 column 1",
        "jsondecodeerror",
    )
    return any(marker in message for marker in markers)


def _extract_chat_text(output: Any) -> str:
    if isinstance(output, ChatOutput):
        return str(output.answer or "").strip()

    if isinstance(output, dict):
        answer = output.get("answer")
        if str(answer or "").strip():
            return str(answer).strip()
        if "content" in output:
            return _stringify_content(output.get("content")).strip()

    answer_attr = getattr(output, "answer", None)
    if str(answer_attr or "").strip():
        return str(answer_attr).strip()

    if hasattr(output, "content"):
        return _stringify_content(getattr(output, "content", "")).strip()

    return ""


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


def _build_context_enrichment_user_prompt(
    *,
    user_text: str,
    schema_summary: str,
    known_columns: list[dict[str, str]],
    missing_context: list[str],
    retry_feedback: str,
    enrichment_hints: list[str],
    prior_search_summary: str,
    tool_budget_remaining: int,
) -> str:
    known_columns_json = _safe_json_dumps(known_columns[:20])
    missing_json = _safe_json_dumps(missing_context[:6])
    hints_json = _safe_json_dumps(enrichment_hints[:8])
    feedback = _truncate_text(retry_feedback, limit=500)
    summary = _truncate_text(schema_summary, limit=2200)
    return (
        "User question:\n"
        f"{_truncate_text(user_text, limit=600)}\n\n"
        "Schema summary:\n"
        f"{summary}\n\n"
        f"Known columns JSON:\n{known_columns_json}\n\n"
        f"Missing context hints JSON:\n{missing_json}\n\n"
        f"Search keyword hints JSON:\n{hints_json}\n\n"
        f"Prior search context:\n{_truncate_text(prior_search_summary, limit=1200) or 'none'}\n\n"
        f"Retry feedback:\n{feedback or 'none'}\n\n"
        f"Tool call budget remaining: {max(0, int(tool_budget_remaining))}\n"
        "If context is sufficient, do not call tools and return final JSON immediately."
    )


def _summarize_prior_search_context(enrichment_results: dict[str, Any] | None) -> str:
    results = enrichment_results if isinstance(enrichment_results, dict) else {}
    lines: list[str] = []
    search_rows = results.get("search_schema")
    if isinstance(search_rows, list):
        for item in search_rows[-6:]:
            if not isinstance(item, dict):
                continue
            query = str(item.get("query") or "").strip()
            queries = [str(q).strip() for q in (item.get("queries") or []) if str(q).strip()]
            match_count = int(item.get("match_count") or 0)
            columns = item.get("columns") if isinstance(item.get("columns"), list) else []
            matched_cols = [str(col.get("name") or "").strip() for col in columns if isinstance(col, dict)]
            matched_cols = [name for name in matched_cols if name][:4]
            query_label = ", ".join(queries[:6]) if queries else query
            lines.append(
                f"search_schema[{query_label or 'unknown'}] -> matches={match_count}, cols={', '.join(matched_cols) or 'none'}"
            )

    chunk_rows = results.get("scan_schema_chunks")
    if isinstance(chunk_rows, list):
        for item in chunk_rows[-4:]:
            if not isinstance(item, dict):
                continue
            terms = [str(term).strip() for term in (item.get("query_terms") or []) if str(term).strip()]
            rel = int(item.get("relevant_table_count") or 0)
            lines.append(
                f"scan_schema_chunks[{', '.join(terms[:6]) or 'none'}] -> relevant_tables={rel}"
            )
    return "\n".join(lines).strip()


def _parse_context_enrichment_decision(messages: list[AnyMessage]) -> ContextEnrichmentDecision:
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        tool_calls = message.tool_calls if isinstance(message.tool_calls, list) else []
        if tool_calls:
            continue
        payload = _safe_json_loads(_stringify_content(message.content))
        if payload:
            try:
                return ContextEnrichmentDecision.model_validate(payload)
            except Exception:
                continue
    return ContextEnrichmentDecision(enough_context=False, missing_context=[], notes="")


def _parse_tool_message_payload(message: ToolMessage) -> dict[str, Any]:
    content = message.content
    if isinstance(content, dict):
        return content
    if isinstance(content, list):
        combined = _stringify_content(content).strip()
        return _safe_json_loads(combined)
    return _safe_json_loads(str(content or ""))


def _collect_enrichment_updates(
    *,
    messages: list[AnyMessage],
    start_index: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    updates: dict[str, Any] = {}
    discovered_columns: list[dict[str, Any]] = []
    relevant_tables: list[dict[str, Any]] = []

    for message in messages[max(0, int(start_index)) :]:
        if not isinstance(message, ToolMessage):
            continue
        tool_name = str(message.name or "").strip()
        payload = _parse_tool_message_payload(message)
        if not payload:
            continue

        if tool_name == "search_schema":
            updates.setdefault("search_schema", []).append(payload)
            cols = payload.get("columns")
            if isinstance(cols, list):
                discovered_columns.extend(cols)
            continue

        if tool_name == "scan_schema_chunks":
            updates.setdefault("scan_schema_chunks", []).append(payload)
            cols = payload.get("columns")
            if isinstance(cols, list):
                discovered_columns.extend(cols)
            relevant_tables.extend(_extract_relevant_tables_from_chunk_result(payload))
            continue

        if tool_name == "sample_data":
            updates["sample_data"] = payload

    return updates, discovered_columns, relevant_tables


def _merge_enrichment_results(
    *,
    current: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(current or {}) if isinstance(current, dict) else {}
    for key in ("search_schema", "scan_schema_chunks"):
        existing_rows = merged.get(key)
        normalized_existing = list(existing_rows) if isinstance(existing_rows, list) else []
        new_rows = incoming.get(key)
        if isinstance(new_rows, list) and new_rows:
            normalized_existing.extend(new_rows)
        if normalized_existing:
            merged[key] = normalized_existing
    if isinstance(incoming.get("sample_data"), dict):
        merged["sample_data"] = incoming["sample_data"]
    return merged


def _latest_tool_payload(
    *,
    messages: list[AnyMessage],
    start_index: int,
    tool_name: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    target = str(tool_name or "").strip()
    for message in messages[max(0, int(start_index)) :]:
        if not isinstance(message, ToolMessage):
            continue
        if str(message.name or "").strip() != target:
            continue
        parsed = _parse_tool_message_payload(message)
        if isinstance(parsed, dict):
            payload = parsed
    return payload


def _fallback_context_assessment(
    *,
    user_text: str,
    known_columns: list[dict[str, Any]],
    table_names: list[str],
) -> dict[str, Any]:
    text = str(user_text or "").strip()
    if not text:
        return {
            "context_sufficiency": {"enough_context": bool(known_columns), "missing_context": ["user question text"]},
            "tool_plan": [],
        }

    tokens = re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())
    token_queries: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        token_queries.append(token)
        if len(token_queries) >= 3:
            break

    missing_context: list[str] = []
    if not known_columns:
        missing_context.append("relevant column names and types")
    if not table_names:
        missing_context.append("candidate tables")

    if not token_queries:
        return {
            "context_sufficiency": {"enough_context": bool(known_columns), "missing_context": missing_context},
            "tool_plan": [],
        }

    return {
        "context_sufficiency": {"enough_context": False, "missing_context": missing_context or ["schema details"]},
        "tool_plan": [{"tool": "search_schema", "query": query, "limit": 20} for query in token_queries],
    }


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
    schema_memory = await asyncio.to_thread(_load_schema_memory_markdown, data_path)
    schema_summary = _build_schema_summary(
        table_names=table_names,
        workspace_schema=workspace_schema,
        known_columns=known_columns,
    )
    if schema_memory:
        schema_summary = (
            f"{schema_summary}\n\n"
            "Distilled schema memory from prior runs:\n"
            f"{schema_memory[:4000]}"
        )
    user_text = _latest_user_text(messages)
    runtime = load_agent_runtime_config()
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    existing_tool_messages = list(state.get("analysis_tool_messages") or [])
    reset_tool_messages = [
        RemoveMessage(id=str(getattr(message, "id")))
        for message in existing_tool_messages
        if str(getattr(message, "id", "")).strip()
    ]
    existing_runtime_messages = list(state.get("analysis_runtime_tool_messages") or [])
    reset_runtime_tool_messages = [
        RemoveMessage(id=str(getattr(message, "id")))
        for message in existing_runtime_messages
        if str(getattr(message, "id", "")).strip()
    ]

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
            "schema_memory": schema_memory,
        },
        "known_columns": known_columns,
        "attempt_counters": {
            "generation": int(attempt_counters.get("generation") or 0),
            "execution": int(attempt_counters.get("execution") or 0),
            "enrichment": int(attempt_counters.get("enrichment") or 0),
            "max_code_executions": max(1, int(runtime.max_code_executions)),
            "max_tool_calls": max(1, int(runtime.max_tool_calls)),
        },
        "enrichment_results": {},
        "enrichment_hints": [],
        "enrichment_tool_cursor": 0,
        "analysis_tool_messages": reset_tool_messages,
        "analysis_runtime_tool_messages": reset_runtime_tool_messages,
        "runtime_tool_cursor": 0,
        "runtime_tool_stage": "",
        "retry_feedback": "",
    }


async def analysis_assess_context_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    messages = list(analysis_context.get("messages") or [])
    user_text = str(analysis_context.get("user_text") or "")
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    table_names = _normalize_table_names(analysis_context.get("table_names"), max_items=16)
    schema_summary = _truncate_text(str(analysis_context.get("schema_summary") or ""), limit=1800)
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
    model = _get_model(config, lite=False)
    chain = prompt | model.with_structured_output(AnalysisContextAssessment)
    try:
        output = await _ainvoke_structured_chain(
            chain,
            {
                "user_text": _truncate_text(user_text, limit=400),
                "schema_summary": schema_summary,
                "known_columns_json": _safe_json_dumps(known_columns[:20]),
                "retry_feedback": _truncate_text(str(state.get("retry_feedback") or ""), limit=400),
                "message_count": len(messages),
            },
        )
        if isinstance(output, AnalysisContextAssessment):
            assessed = output
        else:
            assessed = AnalysisContextAssessment.model_validate(output)
    except Exception as exc:
        # Structured parsing may fail when provider truncates response (length finish).
        if "LengthFinishReasonError" not in type(exc).__name__ and "length limit" not in str(exc).lower():
            raise
        fallback = _fallback_context_assessment(
            user_text=user_text,
            known_columns=known_columns,
            table_names=table_names,
        )
        return fallback

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
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    context_sufficiency = state.get("context_sufficiency") if isinstance(state.get("context_sufficiency"), dict) else {}
    missing_context = [
        str(item).strip()
        for item in (context_sufficiency.get("missing_context") or [])
        if str(item).strip()
    ][:6]
    retry_feedback = str(state.get("retry_feedback") or "").strip()
    hints = _normalize_search_queries(state.get("enrichment_hints") or [])
    existing_results = state.get("enrichment_results") if isinstance(state.get("enrichment_results"), dict) else {}
    prior_search_summary = _summarize_prior_search_context(existing_results)
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    max_tool_calls = max(1, int(attempt_counters.get("max_tool_calls") or 5))

    existing_messages = list(state.get("analysis_tool_messages") or [])
    executed_tool_calls = sum(1 for message in existing_messages if isinstance(message, ToolMessage))
    tool_budget_remaining = max(0, max_tool_calls - executed_tool_calls)

    seed_messages: list[AnyMessage] = []
    should_seed = not existing_messages
    retry_target = str(state.get("retry_target") or "").strip()
    if should_seed:
        seed_messages.append(SystemMessage(content=_CONTEXT_ENRICHMENT_TOOL_PROMPT))
        seed_messages.append(
            HumanMessage(
                content=_build_context_enrichment_user_prompt(
                    user_text=str(analysis_context.get("user_text") or ""),
                    schema_summary=str(analysis_context.get("schema_summary") or ""),
                    known_columns=known_columns,
                    missing_context=missing_context,
                    retry_feedback=retry_feedback,
                    enrichment_hints=hints,
                    prior_search_summary=prior_search_summary,
                    tool_budget_remaining=tool_budget_remaining,
                )
            )
        )
    elif retry_target == "analysis_enrich_context" and (retry_feedback or hints):
        seed_messages.append(
            HumanMessage(
                content=_build_context_enrichment_user_prompt(
                    user_text=str(analysis_context.get("user_text") or ""),
                    schema_summary=str(analysis_context.get("schema_summary") or ""),
                    known_columns=known_columns,
                    missing_context=missing_context,
                    retry_feedback=retry_feedback,
                    enrichment_hints=hints,
                    prior_search_summary=prior_search_summary,
                    tool_budget_remaining=tool_budget_remaining,
                )
            )
        )

    if tool_budget_remaining <= 0:
        fallback_decision = ContextEnrichmentDecision(
            enough_context=bool(known_columns),
            missing_context=missing_context,
            notes="Tool budget reached; continue with currently available schema context.",
        )
        return {
            "analysis_tool_messages": seed_messages
            + [AIMessage(content=_safe_json_dumps(fallback_decision.model_dump()))],
            "retry_target": "",
            "tool_plan": [],
            "enrichment_hints": [],
        }

    _emit_agent_status(
        step="assessing_context",
        message="Assessing schema context...",
        detail="Deciding whether more schema/data lookup is required before code generation.",
        next_action="If needed, call schema tools via ToolNode.",
    )

    model = _get_model(config, lite=False)
    model_with_tools = model.bind_tools(CONTEXT_ENRICHMENT_TOOLS)
    response = await model_with_tools.ainvoke(existing_messages + seed_messages)
    if not isinstance(response, AIMessage):
        response = AIMessage(content=_stringify_content(getattr(response, "content", response)))

    return {
        "analysis_tool_messages": seed_messages + [response],
        "retry_target": "",
        "tool_plan": [],
    }


def analysis_enrich_to_next(state: dict[str, Any]) -> str:
    route = tools_condition(state, messages_key="analysis_tool_messages")
    if route == "tools":
        return "analysis_enrich_context_tools"
    return "analysis_finalize_context_enrichment"


async def analysis_finalize_context_enrichment_node(
    state: dict[str, Any], config: RunnableConfig
) -> dict[str, Any]:
    _ = config
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    existing_results = state.get("enrichment_results") if isinstance(state.get("enrichment_results"), dict) else {}
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    messages = list(state.get("analysis_tool_messages") or [])
    cursor = max(0, int(state.get("enrichment_tool_cursor") or 0))
    updates, discovered_columns, relevant_tables = _collect_enrichment_updates(
        messages=messages,
        start_index=cursor,
    )
    if discovered_columns:
        known_columns = _merge_known_columns_lru(known_columns, discovered_columns, max_items=50)

    merged_results = _merge_enrichment_results(current=existing_results, incoming=updates)
    decision = _parse_context_enrichment_decision(messages)
    missing_context = [
        str(item).strip()
        for item in (decision.missing_context or [])
        if str(item).strip()
    ][:6]

    schema_memory_path = await asyncio.to_thread(
        _write_schema_memory_markdown,
        data_path=str(analysis_context.get("data_path") or "") or None,
        user_text=str(analysis_context.get("user_text") or ""),
        known_columns=known_columns,
        relevant_tables=relevant_tables,
    )

    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    return {
        "known_columns": known_columns,
        "enrichment_results": merged_results,
        "schema_memory_path": schema_memory_path,
        "context_sufficiency": {
            "enough_context": bool(decision.enough_context or bool(known_columns)),
            "missing_context": missing_context,
            "notes": str(decision.notes or "").strip(),
        },
        "enrichment_tool_cursor": len(messages),
        "enrichment_hints": [],
        "tool_plan": [],
        "attempt_counters": {
            **attempt_counters,
            "enrichment": int(attempt_counters.get("enrichment") or 0) + 1,
        },
    }


async def analysis_prepare_sample_tool_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    enrichment_results = state.get("enrichment_results") if isinstance(state.get("enrichment_results"), dict) else {}
    cached_sample = enrichment_results.get("sample_data")
    if isinstance(cached_sample, dict):
        return {"runtime_tool_stage": ""}

    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    sample_table = str(analysis_context.get("sample_table") or "").strip()
    tool_call = {
        "name": "sample_data_runtime",
        "args": {
            "table_name": sample_table,
            "limit": 5,
            "explanation": "I need a quick sample of the table before generating code.",
        },
        "id": "sample_data_runtime_call",
        "type": "tool_call",
    }
    return {
        "analysis_runtime_tool_messages": [AIMessage(content="", tool_calls=[tool_call])],
        "runtime_tool_stage": "sample",
    }


def analysis_prepare_sample_to_next(state: dict[str, Any]) -> str:
    route = tools_condition(state, messages_key="analysis_runtime_tool_messages")
    if route == "tools":
        return "analysis_runtime_tools"
    return "analysis_generate_code"


async def analysis_capture_sample_tool_result_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    runtime_messages = list(state.get("analysis_runtime_tool_messages") or [])
    cursor = max(0, int(state.get("runtime_tool_cursor") or 0))
    sample_payload = _latest_tool_payload(
        messages=runtime_messages,
        start_index=cursor,
        tool_name="sample_data_runtime",
    )
    enrichment_results = state.get("enrichment_results") if isinstance(state.get("enrichment_results"), dict) else {}
    merged = dict(enrichment_results)
    if sample_payload:
        merged["sample_data"] = sample_payload
    return {
        "enrichment_results": merged,
        "runtime_tool_cursor": len(runtime_messages),
        "runtime_tool_stage": "",
    }


async def analysis_request_execute_tool_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    _ = config
    code = str(state.get("candidate_code") or "").strip()
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
    tool_call = {
        "name": "execute_python_runtime",
        "args": {
            "code": code,
            "timeout": timeout,
            "explanation": "I have candidate code and need to run it to verify the result.",
        },
        "id": f"execute_python_runtime_{execution_attempts}",
        "type": "tool_call",
    }
    return {
        "analysis_runtime_tool_messages": [AIMessage(content="", tool_calls=[tool_call])],
        "runtime_tool_stage": "execute",
    }


def analysis_request_execute_to_next(state: dict[str, Any]) -> str:
    route = tools_condition(state, messages_key="analysis_runtime_tool_messages")
    if route == "tools":
        return "analysis_runtime_tools"
    return "analysis_retry_decider"


async def analysis_capture_execute_tool_result_node(
    state: dict[str, Any], config: RunnableConfig
) -> dict[str, Any]:
    _ = config
    runtime_messages = list(state.get("analysis_runtime_tool_messages") or [])
    cursor = max(0, int(state.get("runtime_tool_cursor") or 0))
    execution_payload = _latest_tool_payload(
        messages=runtime_messages,
        start_index=cursor,
        tool_name="execute_python_runtime",
    )
    execution_result = execution_payload if isinstance(execution_payload, dict) else {}
    if not execution_result:
        execution_result = {
            "success": False,
            "error": "Execution tool did not return a payload.",
            "stderr": "Execution tool payload missing",
            "stdout": "",
            "artifacts": [],
        }
    attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
    return {
        "execution_result": execution_result,
        "final_executed_code": str(state.get("candidate_code") or "").strip(),
        "runtime_tool_cursor": len(runtime_messages),
        "runtime_tool_stage": "",
        "attempt_counters": {
            **attempt_counters,
            "execution": int(attempt_counters.get("execution") or 0) + 1,
        },
    }


async def analysis_request_validate_result_tool_node(
    state: dict[str, Any], config: RunnableConfig
) -> dict[str, Any]:
    _ = config
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    _emit_agent_status(
        step="analyzing_results",
        message="Analyzing results...",
        detail="Summarizing runtime output and preparing final user-facing findings.",
        next_action="Generate final explanation.",
    )
    tool_call = {
        "name": "validate_result_runtime",
        "args": {
            "execution_result": execution,
            "explanation": "The code ran, so I am checking whether the output is actually useful.",
        },
        "id": "validate_result_runtime_call",
        "type": "tool_call",
    }
    return {
        "analysis_runtime_tool_messages": [AIMessage(content="", tool_calls=[tool_call])],
        "runtime_tool_stage": "validate",
    }


def analysis_request_validate_to_next(state: dict[str, Any]) -> str:
    route = tools_condition(state, messages_key="analysis_runtime_tool_messages")
    if route == "tools":
        return "analysis_runtime_tools"
    return "analysis_finalize_failure"


def analysis_runtime_tools_to_next(state: dict[str, Any]) -> str:
    stage = str(state.get("runtime_tool_stage") or "").strip().lower()
    if stage == "sample":
        return "analysis_capture_sample_tool_result"
    if stage == "execute":
        return "analysis_capture_execute_tool_result"
    if stage == "validate":
        return "analysis_validate_result"
    return "analysis_retry_decider"


async def analysis_generate_code_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    messages = list(analysis_context.get("messages") or [])
    known_columns = _normalize_known_columns(state.get("known_columns") or [], max_items=50)
    sample_table = str(analysis_context.get("sample_table") or "").strip() or None
    sample = state.get("enrichment_results", {}).get("sample_data") if isinstance(state.get("enrichment_results"), dict) else None
    if not isinstance(sample, dict):
        sample = {"rows": [], "columns": [], "row_count": 0}

    retry_feedback = str(state.get("retry_feedback") or "").strip()
    schema_memory = str(analysis_context.get("schema_memory") or "").strip()
    generation_context = str(analysis_context.get("context") or "")
    if schema_memory:
        generation_context = (
            f"{generation_context}\n\n"
            "Use this schema memory as analyst notes before writing code:\n"
            f"{schema_memory[:5000]}"
        ).strip()
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
        context=generation_context,
        invoke_structured_chain=_ainvoke_structured_chain,
    )
    candidate_code = str(output.code or "").strip()
    requested_queries = _normalize_search_queries(output.search_schema_queries)
    if not requested_queries:
        requested_queries = _extract_search_queries_from_code(candidate_code)
    if requested_queries:
        attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
        next_generation_attempt = int(attempt_counters.get("generation") or 0) + 1
        max_generation_attempts = max(1, int(attempt_counters.get("max_code_executions") or 3))
        if next_generation_attempt >= max_generation_attempts:
            return {
                "analysis_output": output.model_dump(),
                "candidate_code": "",
                "tool_plan": [],
                "enrichment_hints": requested_queries,
                "retry_target": "",
                "retry_feedback": (
                    "Code generation repeatedly requested additional schema lookup and reached the retry limit. "
                    "Finalize with a clear failure summary."
                ),
                "attempt_counters": {
                    **attempt_counters,
                    "generation": next_generation_attempt,
                },
            }
        return {
            "analysis_output": output.model_dump(),
            "candidate_code": "",
            "tool_plan": [],
            "enrichment_hints": requested_queries,
            "retry_target": "analysis_enrich_context",
            "retry_feedback": (
                "Code generation requested additional schema lookup. "
                "Run the context enrichment loop before the next generation attempt."
            ),
            "attempt_counters": {
                **attempt_counters,
                "generation": next_generation_attempt,
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
    # Deprecated shim kept for compatibility with older imports. Active graph uses ToolNode path.
    return await analysis_request_execute_tool_node(state, config)


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
        hints = _extract_schema_query_keywords(error_text, max_items=3)
        return {
            "retry_feedback": f"Execution failed due to missing schema context: {error_text[:1200]}",
            "retry_target": "analysis_enrich_context",
            "enrichment_hints": hints,
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
    _ = config
    execution = state.get("execution_result") if isinstance(state.get("execution_result"), dict) else {}
    runtime_messages = list(state.get("analysis_runtime_tool_messages") or [])
    runtime_cursor = max(0, int(state.get("runtime_tool_cursor") or 0))
    tool_summary = _latest_tool_payload(
        messages=runtime_messages,
        start_index=runtime_cursor,
        tool_name="validate_result_runtime",
    )
    result_summary = tool_summary if isinstance(tool_summary, dict) else {}
    if not result_summary:
        result_summary = {
            "success": bool(execution.get("success")),
            "stdout": str(execution.get("stdout") or "").strip()[:1800],
            "stderr": str(execution.get("stderr") or execution.get("error") or "").strip()[:1800],
            "result_type": str(execution.get("result_type") or ""),
            "result_kind": str(execution.get("result_kind") or ""),
            "result_name": str(execution.get("result_name") or ""),
            "result_preview": "",
            "artifact_count": len([item for item in (execution.get("artifacts") or []) if isinstance(item, dict)]),
            "artifacts": [item for item in (execution.get("artifacts") or []) if isinstance(item, dict)],
        }
    artifacts = [item for item in (result_summary.get("artifacts") or []) if isinstance(item, dict)]
    analysis_context = state.get("analysis_context") if isinstance(state.get("analysis_context"), dict) else {}
    code = str(state.get("candidate_code") or "").strip()
    analysis_output = state.get("analysis_output") if isinstance(state.get("analysis_output"), dict) else {}
    code_explanation = str(analysis_output.get("explanation") or "").strip()
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

    result_kind = str(result_summary.get("result_kind") or "").strip().lower()
    artifact_count = int(result_summary.get("artifact_count") or 0)
    has_stdout_signal = bool(str(result_summary.get("stdout") or "").strip())
    has_result_signal = result_kind in {"dataframe", "figure", "scalar"}
    validation_outcome = {"status": "ok", "reason": ""}
    retry_feedback = ""
    retry_target = ""
    if not (artifact_count > 0 or has_result_signal or has_stdout_signal):
        validation_outcome = {
            "status": "retry",
            "reason": (
                "Execution produced no analyzable output. "
                "Generate code that returns a dataframe, figure, or scalar result."
            ),
        }
        retry_feedback = str(validation_outcome["reason"])
        retry_target = "analysis_generate_code"

    return {
        "final_execution": execution,
        "final_artifacts": artifacts,
        "result_summary": result_summary,
        "result_explanation": result_explanation,
        "code_explanation": code_explanation,
        "runtime_tool_cursor": len(runtime_messages),
        "runtime_tool_stage": "",
        "validation_outcome": validation_outcome,
        "retry_feedback": retry_feedback,
        "retry_target": retry_target,
    }


def analysis_validate_to_next(state: dict[str, Any]) -> str:
    outcome = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    if str(outcome.get("status") or "").strip().lower() == "retry":
        attempt_counters = state.get("attempt_counters") if isinstance(state.get("attempt_counters"), dict) else {}
        generation_attempts = int(attempt_counters.get("generation") or 0)
        max_attempts = max(1, int(attempt_counters.get("max_code_executions") or 3))
        if generation_attempts >= max_attempts:
            return "analysis_finalize_failure"
        return "analysis_generate_code"
    return "analysis_finalize_success"


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
    _ = config
    # Deprecated shim retained only for backwards compatibility; active graph does not route here.
    text = (
        "The legacy react_loop execution path is disabled. "
        "Use the native ToolNode-backed analysis graph path."
    )
    return {
        "route": "analysis",
        "final_code": "",
        "final_explanation": text,
        "result_explanation": text,
        "code_explanation": "",
        "final_execution": None,
        "final_artifacts": [],
        "final_executed_code": "",
        "output_contract": [],
        "metadata": {"is_safe": True, "is_relevant": True},
        "messages": [AIMessage(content=text)],
        "last_error": text,
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
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
    messages_payload = {"messages": list(state.get("messages") or [])}
    chain = prompt | model.with_structured_output(ChatOutput)
    try:
        output = await _ainvoke_structured_chain(chain, messages_payload)
    except Exception as exc:
        if not _is_empty_json_structured_parse_error(exc):
            raise
        fallback_chain = prompt | model
        output = await _ainvoke_structured_chain(fallback_chain, messages_payload)

    text = _extract_chat_text(output)
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

    return {
        "final_code": code,
        "final_explanation": result_explanation,
        "result_explanation": result_explanation,
        "code_explanation": code_explanation,
        "final_execution": state.get("final_execution"),
        "final_artifacts": state.get("final_artifacts") or [],
        "final_executed_code": state.get("final_executed_code") or "",
        "messages": [AIMessage(content=result_explanation)],
        "output_contract": state.get("output_contract") or [],
        "known_columns": _normalize_known_columns(state.get("known_columns") or []),
        "route": state.get("route") or "analysis",
        "metadata": state.get("metadata") or {"is_safe": True, "is_relevant": True},
        "run_id": state.get("run_id"),
    }
