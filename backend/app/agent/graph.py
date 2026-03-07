import os
import re
import warnings
from contextvars import ContextVar

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import add_messages, StateGraph, START, END
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)
from langgraph.graph.state import CompiledStateGraph, Checkpointer
from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv

from typing import Annotated, Any, cast, Mapping
from collections.abc import Iterator
from collections.abc import Callable

import json
from pathlib import Path
from .code_guard import guard_code
from ..core.logger import logprint
from ..services.chat_model_factory import create_chat_model
from ..services.llm_runtime_config import load_llm_runtime_config, normalize_model_id


MAX_CODE_GUARD_RETRIES = 2
_STREAM_TOKEN_EMITTER: ContextVar[Callable[[str, str], None] | None] = ContextVar(
    "_stream_token_emitter",
    default=None,
)


def set_stream_token_emitter(emitter: Callable[[str, str], None] | None):
    return _STREAM_TOKEN_EMITTER.set(emitter)


def reset_stream_token_emitter(token) -> None:
    _STREAM_TOKEN_EMITTER.reset(token)


def emit_stream_token(node_name: str, text: str) -> None:
    emitter = _STREAM_TOKEN_EMITTER.get()
    if not callable(emitter):
        return
    chunk = str(text or "")
    if not chunk:
        return
    emitter(str(node_name or ""), chunk)


def get_prompt_path(filename: str) -> Path:
    """Get absolute path to a prompt file"""
    return Path(__file__).parent.parent / "core" / "prompts" / "yaml" / filename


def load_json(filepath: str | Path):
    with open(filepath, "r") as file:
        schema = json.load(file)

    return schema


load_dotenv()


class MetaData(BaseModel):
    is_safe: bool | None = Field(
        default=None,
        description="if the question asked is not malicious or it cannot corrupt data",
    )
    safety_reasoning: str | None = Field(default=None)
    is_relevant: bool | None = Field(
        default=None,
        description="if the question asked is relevant to the active schema",
    )
    require_code: bool | None = Field(default=None)
    relevancy_reasoning: str | None = Field(default=None)


def merge_metadata(
    prev: MetaData | None, new: MetaData | Mapping[str, Any] | None
) -> MetaData | None:
    try:
        if new is None and prev is None:
            return None

        # Helper to convert input to dict safely
        def to_dict(obj):
            if isinstance(obj, MetaData):
                return obj.model_dump()
            if isinstance(obj, dict):
                return obj
            return {}  # Fallback for bad types (strings, etc)

        prev_dict = to_dict(prev)
        new_dict = to_dict(new)

        # Merge
        merged = prev_dict.copy()
        merged.update(new_dict)

        return MetaData(**merged)
    except Exception as e:
        # Fallback to prevent state corruption/crash
        # We return a fresh MetaData to ensure the graph can continue
        return prev if isinstance(prev, MetaData) else MetaData()


class State(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    metadata: Annotated[MetaData, merge_metadata] = Field(default=MetaData())
    plan: str | None = Field(default=None)
    code: str | None = Field(default=None)
    final_explanation: str | None = Field(default=None)
    active_schema: dict[str, Any] | None = Field(default=None)
    previous_code: str = Field(
        default="", description="previous code used as context for generation"
    )
    current_code: str = Field(
        default="", description="current code which can provide LLM more context"
    )
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)
    context: str = Field(default="")
    code_guard_feedback: str = Field(default="")
    code_guard_retries: int = Field(default=0)
    guard_status: str = Field(default="ok")
    output_contract: list[dict[str, str]] = Field(default_factory=list)


class InputSchema(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    active_schema: dict[str, Any] | None = Field(default=None)
    previous_code: str = Field(
        default="", description="previous code used as context for generation"
    )
    current_code: str = Field(
        default="", description="current code which can provide LLM more context"
    )
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)
    context: str = Field(default="")


class OutputSchema(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    metadata: MetaData | None = Field(default=None)
    plan: str | None = Field(default=None)
    code: str | None = Field(default=None)
    final_explanation: str | None = Field(default=None)
    # We might want to pass these through
    table_name: str | None = Field(default=None)
    data_path: str | None = Field(default=None)
    context: str | None = Field(default=None)
    output_contract: list[dict[str, str]] = Field(default_factory=list)


class InquiraAgent:
    def __init__(self) -> None:
        self.counter = 0

    @staticmethod
    def _resolve_runtime_model(
        requested_model: str,
        selected_model: str,
        default_model: str,
        lite_model: str,
    ) -> str:
        legacy_default_models = {"gemini-2.5-flash", "gemini-2.5-pro"}
        legacy_lite_models = {"gemini-2.5-flash-lite", "gemini-2.0-flash-lite"}

        requested_model = (requested_model or "").strip()
        selected_model = normalize_model_id((selected_model or "").strip())
        default_model = normalize_model_id((default_model or "").strip())
        lite_model = normalize_model_id((lite_model or "").strip())

        if selected_model and requested_model in legacy_default_models:
            return selected_model
        if requested_model in legacy_default_models:
            return default_model
        if requested_model in legacy_lite_models:
            return lite_model
        return normalize_model_id(requested_model)

    def _get_model(
        self, config: RunnableConfig, model_name: str = "gemini-2.5-flash"
    ) -> BaseChatModel:
        """Get model instance with API key from config"""
        configurable = config.get("configurable", {})
        api_key = str(configurable.get("api_key") or "").strip()
        selected_model = str(configurable.get("model") or "").strip()
        runtime = load_llm_runtime_config()

        effective_model = self._resolve_runtime_model(
            requested_model=model_name,
            selected_model=selected_model,
            default_model=runtime.default_model,
            lite_model=runtime.lite_model,
        )

        resolved_api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        if runtime.requires_api_key and not resolved_api_key:
            raise ValueError("API key not configured for LLM runtime")

        return create_chat_model(
            provider=runtime.provider,
            model=effective_model,
            api_key=resolved_api_key,
            base_url=runtime.base_url,
            temperature=0,
            max_tokens=runtime.code_generation_max_tokens,
        )

    @staticmethod
    def _normalize_output_contract(contract: Any) -> list[dict[str, str]]:
        if not isinstance(contract, list):
            return []

        kind_aliases = {
            "dataframe": "dataframe",
            "pandas": "dataframe",
            "polars": "dataframe",
            "pyarrow": "dataframe",
            "arrow": "dataframe",
            "figure": "figure",
            "chart": "figure",
            "plotly": "figure",
            "scalar": "scalar",
            "value": "scalar",
            "number": "scalar",
            "text": "scalar",
        }

        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in contract:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
                continue
            dedupe_key = name.lower()
            if dedupe_key in seen:
                continue
            kind = kind_aliases.get(str(item.get("kind") or "").strip().lower(), "")
            if kind not in {"dataframe", "figure", "scalar"}:
                continue
            normalized.append({"name": name, "kind": kind})
            seen.add(dedupe_key)
            if len(normalized) >= 8:
                break
        return normalized

    @staticmethod
    def _invoke_structured_chain(chain: Any, payload: dict[str, Any]) -> Any:
        # Some provider/langchain versions emit noisy pydantic serializer warnings
        # for structured-output model serialization even when the call succeeds.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"^Pydantic serializer warnings:",
                category=UserWarning,
            )
            return chain.invoke(payload)

    @staticmethod
    def _extract_chunk_text(chunk: Any) -> str:
        if chunk is None:
            return ""
        if isinstance(chunk, str):
            return chunk
        content = getattr(chunk, "content", None)
        if content is None:
            return str(chunk)
        return _stringify_content(content)

    @staticmethod
    def _sanitize_plan_text(plan_text: str) -> str:
        text = str(plan_text or "").strip()
        if not text:
            return ""

        # Remove fenced code blocks so the plan stays analytical and code-free.
        sanitized = re.sub(
            r"```[\s\S]*?```",
            "[Code snippet removed from plan output]",
            text,
            flags=re.IGNORECASE,
        )

        # Drop highly code-like single lines that may still leak through.
        filtered_lines: list[str] = []
        removed_code_line = False
        for raw_line in sanitized.splitlines():
            line = raw_line.strip()
            if not line:
                filtered_lines.append("")
                continue
            looks_like_assignment = re.search(
                r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*.+",
                line,
            )
            has_import_stmt = re.search(
                r"^(from\s+[A-Za-z0-9_.]+\s+import|import\s+[A-Za-z0-9_. ,]+)",
                line,
                flags=re.IGNORECASE,
            )
            has_sql_stmt = re.search(
                r"^(with|select|update|delete|insert)\b",
                line,
                flags=re.IGNORECASE,
            )
            has_library_call = re.search(
                r"\b(duckdb|pandas|plotly|conn|pd|px|df)\.[A-Za-z_][A-Za-z0-9_]*\(",
                line,
            )
            if looks_like_assignment or has_import_stmt or has_sql_stmt or has_library_call:
                removed_code_line = True
                continue
            filtered_lines.append(raw_line)

        sanitized = "\n".join(filtered_lines).strip()
        sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
        if removed_code_line and sanitized:
            sanitized = (
                f"{sanitized}\n\nNote: Code-like lines were removed to keep this plan plain English."
            )
        return sanitized

    @staticmethod
    def _split_code_into_chunks(
        code: str,
        *,
        min_sections: int = 3,
        max_sections: int = 6,
    ) -> list[str]:
        text = str(code or "").strip()
        if not text:
            return []

        chunks = [
            part.strip("\n")
            for part in re.split(r"\n{2,}", text)
            if part and part.strip()
        ]
        if not chunks:
            return []

        while len(chunks) > max_sections:
            chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}"
            chunks.pop()

        # If the model/code gives too few chunks, split the longest blocks.
        while len(chunks) < min_sections:
            longest_index = max(range(len(chunks)), key=lambda idx: len(chunks[idx]))
            lines = chunks[longest_index].splitlines()
            if len(lines) < 6:
                break
            midpoint = len(lines) // 2
            split_idx = midpoint
            for offset in range(0, 6):
                up = midpoint - offset
                down = midpoint + offset
                if up > 1 and not lines[up].strip():
                    split_idx = up
                    break
                if down < len(lines) - 1 and not lines[down].strip():
                    split_idx = down
                    break
            left = "\n".join(lines[:split_idx]).strip()
            right = "\n".join(lines[split_idx:]).strip()
            if not left or not right:
                break
            chunks[longest_index : longest_index + 1] = [left, right]

        if len(chunks) < min_sections:
            lines = text.splitlines()
            target = min_sections
            chunk_size = max(1, (len(lines) + target - 1) // target)
            rebuilt: list[str] = []
            for start in range(0, len(lines), chunk_size):
                piece = "\n".join(lines[start : start + chunk_size]).strip()
                if piece:
                    rebuilt.append(piece)
            if rebuilt:
                chunks = rebuilt
            while len(chunks) > max_sections:
                chunks[-2] = f"{chunks[-2]}\n{chunks[-1]}"
                chunks.pop()

        return chunks[:max_sections]

    @staticmethod
    def _normalize_explanation_sections(
        raw_sections: Any,
        fallback_code: str,
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []

        if isinstance(raw_sections, list):
            for idx, section in enumerate(raw_sections, start=1):
                item = section
                if hasattr(section, "model_dump"):
                    item = section.model_dump()
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or f"Step {idx}").strip()
                language = str(item.get("language") or "python").strip().lower()
                if language not in {"python", "sql"}:
                    language = "python"
                code = str(item.get("code") or "").strip()
                explanation = str(item.get("explanation") or "").strip()
                if not code or not explanation:
                    continue
                normalized.append(
                    {
                        "title": title or f"Step {idx}",
                        "language": language,
                        "code": code,
                        "explanation": explanation,
                    }
                )

        if normalized:
            return normalized[:6]

        fallback_chunks = InquiraAgent._split_code_into_chunks(fallback_code)
        fallback_sections: list[dict[str, str]] = []
        for idx, chunk in enumerate(fallback_chunks, start=1):
            looks_like_sql = bool(
                re.search(r"^\s*(with|select|update|delete|insert)\b", chunk, re.IGNORECASE)
            )
            fallback_sections.append(
                {
                    "title": f"Step {idx}",
                    "language": "sql" if looks_like_sql else "python",
                    "code": chunk,
                    "explanation": (
                        "This block handles one part of the workflow and passes results to the next step."
                    ),
                }
            )
        return fallback_sections[:6]

    @staticmethod
    def _compose_sectioned_explanation(
        *,
        overview: str,
        sections: list[dict[str, str]],
        next_step: str,
        follow_up_question: str,
    ) -> str:
        parts: list[str] = []
        clean_overview = str(overview or "").strip()
        if clean_overview:
            parts.append(f"### Overview\n{clean_overview}")

        for idx, section in enumerate(sections, start=1):
            title = str(section.get("title") or f"Step {idx}").strip()
            language = str(section.get("language") or "python").strip().lower()
            if language not in {"python", "sql"}:
                language = "python"
            code = str(section.get("code") or "").strip()
            explanation = str(section.get("explanation") or "").strip()
            if not code or not explanation:
                continue
            parts.append(
                f"### {idx}. {title}\n"
                f"```{language}\n{code}\n```\n"
                f"{explanation}"
            )

        safe_next_step = str(next_step or "").strip() or "Run the code and review the output."
        parts.append(f"### Next step\n{safe_next_step}")

        safe_follow_up = str(follow_up_question or "").strip()
        if not safe_follow_up:
            safe_follow_up = "How can I help you next?"
        if not safe_follow_up.endswith("?"):
            safe_follow_up = f"{safe_follow_up}?"
        parts.append(safe_follow_up)

        return "\n\n".join(part for part in parts if part.strip())

    def _invoke_text_chain_with_streaming(
        self,
        chain: Any,
        payload: dict[str, Any],
        *,
        node_name: str,
    ) -> AIMessage:
        collected_parts: list[str] = []

        try:
            for chunk in chain.stream(payload):
                text = self._extract_chunk_text(chunk)
                if not text:
                    continue
                emit_stream_token(node_name, text)
                collected_parts.append(text)
        except Exception:
            # Fall back to normal invoke path if provider/runtime cannot stream chunks.
            response = chain.invoke(payload)
            return AIMessage(content=_stringify_content(getattr(response, "content", response)))

        if collected_parts:
            return AIMessage(content="".join(collected_parts))

        response = chain.invoke(payload)
        return AIMessage(content=_stringify_content(getattr(response, "content", response)))

    @staticmethod
    def _emit_text_stream_chunks(
        node_name: str,
        text: str,
        *,
        chunk_size: int = 24,
    ) -> None:
        content = str(text or "")
        if not content:
            return
        safe_chunk_size = max(1, int(chunk_size))
        for start_idx in range(0, len(content), safe_chunk_size):
            emit_stream_token(node_name, content[start_idx : start_idx + safe_chunk_size])

    def check_relevancy(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class IsRelevant(BaseModel):
            is_relevant: bool | None = Field(
                default=None,
                description="if the question asked is relevant to the active schema",
            )
            relevancy_reasoning: str | None = Field(default=None)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("is_relevant_prompt.yaml"), input_variables=["schema"]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(IsRelevant)

        response = self._invoke_structured_chain(
            chain,
            {"messages": state.messages, "schema": state.active_schema},
        )
        response = cast(IsRelevant, response)

        return {
            "metadata": {
                "is_relevant": response.is_relevant,
                "relevancy_reasoning": response.relevancy_reasoning,
            },
        }

    def check_safety(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class IsSafe(BaseModel):
            is_safe: bool | None = Field(
                default=None,
                description="if the question asked is not malicious or it cannot corrupt data",
            )
            safety_reasoning: str | None = Field(default=None)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("is_safe_prompt.yaml"), input_variables=[]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(IsSafe)

        response = self._invoke_structured_chain(chain, {"messages": state.messages})
        response = cast(IsSafe, response)

        return {
            "metadata": {
                "is_safe": response.is_safe,
                "safety_reasoning": response.safety_reasoning,
            },
        }

    def require_code(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class RequireCode(BaseModel):
            require_code: bool | None

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("require_code_prompt.yaml"), input_variables=["schema"]
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model.with_structured_output(RequireCode)

        response = self._invoke_structured_chain(
            chain,
            {"messages": state.messages, "schema": state.active_schema},
        )
        response = cast(RequireCode, response)

        return {
            "metadata": {
                "require_code": response.require_code,
            }
        }

    def create_plan(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("create_plan_prompt.yaml"),
            input_variables=["schema", "current_code", "context"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model

        response = self._invoke_text_chain_with_streaming(
            chain,
            {
                "messages": state.messages,
                "schema": state.active_schema,
                "current_code": state.previous_code,
                "context": state.context or "",
            },
            node_name="create_plan",
        )
        plan_text = _stringify_content(getattr(response, "content", "")).strip()
        return {"plan": self._sanitize_plan_text(plan_text)}

    def code_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class Code(BaseModel):
            code: str | None
            output_contract: list[dict[str, str]] = Field(default_factory=list)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("codegen_prompt.yaml"),
            input_variables=[
                "plan",
                "current_code",
                "table_name",
                "schema",
                "data_path",
                "context",
            ],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        # Serialize schema to string for the prompt
        schema_str = (
            json.dumps(state.active_schema, indent=2) if state.active_schema else "{}"
        )

        # Use real backend data path for desktop/server-side execution.
        data_path = state.data_path or "data.csv"

        # Upgrade model to ensure code generation capability
        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model.with_structured_output(Code)

        response = self._invoke_structured_chain(
            chain,
            {
                "messages": state.messages,
                "plan": state.plan,
                "current_code": state.previous_code,
                "table_name": state.table_name or "data_table",
                "schema": schema_str,
                "data_path": data_path,
                "context": state.context or "",
            },
        )
        response = cast(Code, response)

        updates = {
            "code": response.code,
            "output_contract": self._normalize_output_contract(response.output_contract),
        }
        if response.code and response.code.strip():
            updates["current_code"] = response.code

        thread_id = config.get("configurable", {}).get("thread_id", "-")
        generated = (response.code or "").strip()
        logprint(
            "[Agent] code_generator produced candidate code",
            level="DEBUG",
            request_id=thread_id,
            code_len=len(generated),
            has_await_query=("await query(" in generated),
        )

        return updates

    def retry_code_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        class Code(BaseModel):
            code: str | None
            output_contract: list[dict[str, str]] = Field(default_factory=list)

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("codegen_prompt.yaml"),
            input_variables=[
                "plan",
                "current_code",
                "table_name",
                "schema",
                "data_path",
                "context",
            ],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        schema_str = (
            json.dumps(state.active_schema, indent=2) if state.active_schema else "{}"
        )
        data_path = state.data_path or "data.csv"

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model.with_structured_output(Code)
        retry_feedback = state.code_guard_feedback or (
            "Ensure code is valid."
        )
        retry_messages = list(state.messages) + [
            HumanMessage(
                content=(
                    "Code validation failed. Regenerate code.\n"
                    f"Validator feedback: {retry_feedback}"
                )
            )
        ]
        response = self._invoke_structured_chain(
            chain,
            {
                "messages": retry_messages,
                "plan": state.plan,
                "current_code": state.code or state.previous_code,
                "table_name": state.table_name or "data_table",
                "schema": schema_str,
                "data_path": data_path,
                "context": state.context or "",
            },
        )
        response = cast(Code, response)

        updates = {
            "code": response.code,
            "output_contract": self._normalize_output_contract(response.output_contract),
        }
        if response.code and response.code.strip():
            updates["current_code"] = response.code

        thread_id = config.get("configurable", {}).get("thread_id", "-")
        generated = (response.code or "").strip()
        logprint(
            "[Agent] retry_code_generator produced candidate code",
            level="DEBUG",
            request_id=thread_id,
            code_len=len(generated),
            has_await_query=("await query(" in generated),
            retry_count=int(state.code_guard_retries or 0),
        )
        return updates

    def noncode_generator(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("noncode_prompt.yaml"),
            input_variables=["schema", "current_code", "context"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model

        response = self._invoke_text_chain_with_streaming(
            chain,
            {
                "messages": state.messages,
                "schema": state.active_schema,
                "current_code": state.previous_code,
                "context": state.context or "",
            },
            node_name="noncode_generator",
        )

        return {"messages": [AIMessage(content=_stringify_content(getattr(response, "content", "")))]}

    def code_guard(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        # Preserve visibility into model output: if retry generation returns empty code,
        # fall back to the last non-empty candidate in current_code.
        candidate_code = state.code if (state.code or "").strip() else state.current_code
        result = guard_code(candidate_code or "", table_name=state.table_name)
        thread_id = config.get("configurable", {}).get("thread_id", "-")
        retries = int(state.code_guard_retries or 0)

        if not result.blocked:
            logprint(
                "[Agent] code_guard accepted candidate code",
                level="DEBUG",
                request_id=thread_id,
                code_len=len(result.code or ""),
                retry_count=retries,
            )
            return {
                "code": result.code,
                "current_code": result.code,
                "guard_status": "ok",
                "code_guard_feedback": "",
            }

        if retries < MAX_CODE_GUARD_RETRIES and result.should_retry:
            logprint(
                "[Agent] code_guard rejected candidate code and requested retry",
                level="WARNING",
                request_id=thread_id,
                retry_count=retries,
                max_retries=MAX_CODE_GUARD_RETRIES,
                reason=result.reason or "",
            )
            return {
                "guard_status": "retry",
                "code_guard_retries": retries + 1,
                "code_guard_feedback": result.reason or "",
                "output_contract": [],
            }

        logprint(
            "[Agent] code_guard failed closed after retry exhaustion",
            level="ERROR",
            request_id=thread_id,
            retry_count=retries,
            max_retries=MAX_CODE_GUARD_RETRIES,
            reason=result.reason or "",
        )
        return {
            "code": "",
            "current_code": "",
            "guard_status": "failed",
            "code_guard_feedback": result.reason or "",
            "output_contract": [],
        }

    def explain_code(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = SystemMessagePromptTemplate.from_template(
            """You are the AI assistant for Inquira.

Explain the generated Python code to a non-technical user in very simple language.

Rules:
- Break the long code into 3 to 6 logical pieces.
- Each piece must include:
  1) a short heading
  2) a compact fenced code snippet
  3) 2-4 short plain-English lines explaining that snippet
- Use plain words and short sentences.
- Avoid jargon. If a technical word is unavoidable, explain it immediately.
- Explain what output each piece helps create.
- Do not mention internal runtime details that a user does not need.
- Include exactly one concrete next step.
- End with one friendly question asking how you can help next.
- Return markdown only.

Output format:
- Start with: `### Overview`
- For each piece use: `### <number>. <short title>`
- Under each piece include one fenced code block with language tag `python` or `sql`
- After the code block, include the 2-4 plain-English explanation lines
- Add `### Next step` near the end, then one final friendly question on the last line

Plan:
{plan}

Code:
{code}

Guard status:
{guard_status}
""",
            input_variables=["plan", "code", "guard_status"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model

        response = self._invoke_text_chain_with_streaming(
            chain,
            {
                "messages": state.messages,
                "plan": state.plan or "",
                "code": state.current_code or state.code or "",
                "guard_status": state.guard_status or "ok",
            },
            node_name="explain_code",
        )
        explanation = _stringify_content(getattr(response, "content", "")).strip()
        if not explanation:
            explanation = (
                "### What I changed\n"
                "I generated code to answer your question.\n\n"
                "### Next step\n"
                "Run the code and review the output table or chart.\n\n"
                "How else can I help next?"
            )
            self._emit_text_stream_chunks("explain_code", explanation)

        return {
            "final_explanation": explanation,
            "messages": [AIMessage(content=explanation)],
        }

    def general_purpose(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        system_prompt_template = """You are the AI assistant for **Inquira**, a data analysis platform.

## About Inquira
Inquira helps users analyze their uploaded data (CSV, Excel, Parquet, JSON) through natural language queries.
The platform uses DuckDB for efficient querying, Pandas for transformations, and Plotly for visualizations.

## Your Capabilities
- Answer questions about the user's uploaded data
- Generate Python code for data analysis and visualization
- Provide statistical insights, aggregations, and business intelligence
- Create charts and dashboards using Plotly

## Guidelines
- Be helpful, friendly, and concise
- If asked about your capabilities, explain what Inquira can do
- For questions unrelated to data analysis, politely redirect to data-focused tasks
- Keep responses brief (2-4 sentences) unless more detail is genuinely needed"""

        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash")
        chain = prompt | model

        response = self._invoke_text_chain_with_streaming(
            chain,
            {"messages": state.messages},
            node_name="general_purpose",
        )

        return {"messages": [AIMessage(content=_stringify_content(getattr(response, "content", "")))]}

    def unsafe_rejector(self, state: State, config: RunnableConfig) -> dict[str, Any]:
        reasoning = (
            state.metadata.safety_reasoning
            or "The request was flagged as potentially unsafe."
        )

        system_prompt_template = SystemMessagePromptTemplate.from_template_file(
            get_prompt_path("unsafe_rejection_prompt.yaml"),
            input_variables=["safety_reasoning"],
        )
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt_template, MessagesPlaceholder("messages")]
        )

        model = self._get_model(config, "gemini-2.5-flash-lite")
        chain = prompt | model

        response = self._invoke_text_chain_with_streaming(
            chain,
            {
                "messages": state.messages,
                "safety_reasoning": reasoning,
            },
            node_name="unsafe_rejector",
        )

        return {"messages": [AIMessage(content=_stringify_content(getattr(response, "content", "")))]}

    def compile(self, checkpointer=None) -> CompiledStateGraph:
        builder = StateGraph(
            State, input_schema=InputSchema, output_schema=OutputSchema
        )

        builder.add_node("check_relevancy", self.check_relevancy)
        builder.add_node("check_safety", self.check_safety)
        builder.add_node("require_code", self.require_code)
        builder.add_node("create_plan", self.create_plan)
        builder.add_node("code_generator", self.code_generator)
        builder.add_node("retry_code_generator", self.retry_code_generator)
        builder.add_node("code_guard", self.code_guard)
        builder.add_node("explain_code", self.explain_code)
        builder.add_node("noncode_generator", self.noncode_generator)
        builder.add_node("general_purpose", self.general_purpose)
        builder.add_node("unsafe_rejector", self.unsafe_rejector)

        builder.add_edge(START, "check_safety")

        def safety_router(state: State):
            if state.metadata.is_safe:
                return "safe"
            else:
                return "unsafe"

        builder.add_conditional_edges(
            "check_safety",
            safety_router,
            {"safe": "check_relevancy", "unsafe": "unsafe_rejector"},
        )

        def relevancy_router(state: State):
            if state.metadata.is_relevant:
                return "relevant"
            else:
                return "irrelevant"

        builder.add_conditional_edges(
            "check_relevancy",
            relevancy_router,
            {"relevant": "require_code", "irrelevant": "general_purpose"},
        )

        def code_router(state: State):
            if state.metadata.require_code:
                return "yes"
            else:
                return "no"

        builder.add_conditional_edges(
            "require_code",
            code_router,
            {"yes": "create_plan", "no": "noncode_generator"},
        )

        builder.add_edge("create_plan", "code_generator")
        builder.add_edge("code_generator", "code_guard")
        def code_guard_router(state: State):
            if state.guard_status == "retry":
                return "retry"
            if state.guard_status == "failed":
                return "failed"
            return "ok"

        builder.add_conditional_edges(
            "code_guard",
            code_guard_router,
            {"retry": "retry_code_generator", "failed": END, "ok": "explain_code"},
        )
        builder.add_edge("retry_code_generator", "code_guard")
        builder.add_edge("explain_code", END)
        builder.add_edge("general_purpose", END)
        builder.add_edge("unsafe_rejector", END)

        # builder.add_edge(["check_relevancy", "check_safety"], "router")

        # builder.add_edge("check_relevancy", END)
        # builder.add_edge("check_safety", END)

        return builder.compile(checkpointer=checkpointer)


def build_graph(checkpointer: Checkpointer = None) -> CompiledStateGraph:
    graph = InquiraAgent()
    agent = graph.compile(checkpointer=checkpointer)
    return agent


def execute(
    agent: CompiledStateGraph,
    user_query: str,
    thread_id: str = "adarsh9780:deliveries_schema.json",
):
    cfg: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    _, _, schema_path = thread_id.partition(":")

    if schema_path:
        active_schema = load_json(schema_path)
        state = InputSchema(
            messages=[HumanMessage(content=user_query)],
            active_schema=active_schema,
            current_code="",
        )

        state = agent.invoke(state, config=cfg)

        return state
    else:
        raise ValueError(f"No active schema is provided. current thread: {thread_id}")


def stream_nodes(
    agent: CompiledStateGraph,
    user_query: str,
    thread_id="adarsh9780:deliveries_schema.json",
) -> Iterator:
    cfg: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    _, _, schema_path = thread_id.partition(":")
    init_state = InputSchema(
        messages=[HumanMessage(content=user_query)],
        active_schema=load_json(schema_path),
        current_code="",
    )
    for step in agent.stream(init_state, config=cfg):
        for node_name, payload in step.items():
            # print("STREAM:", node_name, "keys:", list(payload.keys()))
            # print(payload["messages"])
            yield node_name, payload


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [_stringify_content(part) for part in content]
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        if content.get("type") == "text":
            return content.get("text", "")
        return json.dumps(content)
    return str(content)


def convert_ai_messages_to_buffer_string(messages: list[AnyMessage]) -> str:
    msgs: list[str] = []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = _stringify_content(msg.content)
            if text:
                msgs.append(text)
        else:
            break
    return "\n".join(reversed(msgs))


if __name__ == "__main__":
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langchain_core.runnables import RunnableConfig

    with SqliteSaver.from_conn_string("test.db") as memory:
        agent = build_graph(checkpointer=None)

    while True:
        user_query = input("You: ")
        if user_query in ("exit", "quit", "kill", "q", "qut", "qt", "ext"):
            break

        for node_name, payload in stream_nodes(agent, user_query):
            if "messages" in payload:
                text = convert_ai_messages_to_buffer_string(payload["messages"])
                print(f"{node_name}: {text}")
            if "plan" in payload:
                print(f"{node_name} plan:\n{payload['plan']}")
            if "code" in payload:
                print(f"{node_name} plan:\n{payload['code']}")
