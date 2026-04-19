"""Routing logic for agent v2."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Literal

from langchain_core.messages import AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, ConfigDict, Field

from .services.chat_model_factory import create_chat_model
from .services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from .services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key
from .structured_schema import openai_strict_json_schema

_ROUTER_PROMPT = (
    Path(__file__).parent / "prompts" / "router_system.yaml"
).read_text(encoding="utf-8")

_UNSAFE_RE = re.compile(
    r"\b(rm\s+-rf|drop\s+table|truncate\s+table|delete\s+from|exfiltrate|steal|bypass)\b",
    re.IGNORECASE,
)


class RouteDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra=openai_strict_json_schema)

    route: Literal["analysis", "general_chat", "unsafe"]
    reasoning: str = Field(default="")


def _summarize_user_text(user_text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(user_text or "")).strip()
    if not text:
        return "your request"
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}..."


def _fallback_reasoning(route: str, user_text: str) -> str:
    summary = _summarize_user_text(user_text)
    normalized_route = str(route or "").strip().lower()
    if normalized_route == "unsafe":
        return "I understand this request may affect system or data safety, so I need to stop before taking action."
    if normalized_route == "general_chat":
        return f"I understand you are asking about {summary}, so I can answer directly."
    return f"I understand you want to analyze {summary}, so I need to inspect available data context before answering."


def _normalize_decision(candidate: object, user_text: str) -> RouteDecision:
    if isinstance(candidate, RouteDecision):
        route = str(candidate.route or "").strip().lower()
        reasoning = str(candidate.reasoning or "").strip()
    else:
        route = str(getattr(candidate, "route", "") or "").strip().lower()
        reasoning = str(getattr(candidate, "reasoning", "") or "").strip()
    if route not in {"analysis", "general_chat", "unsafe"}:
        route = "analysis"
    if not reasoning:
        reasoning = _fallback_reasoning(route, user_text)
    return RouteDecision(route=route, reasoning=reasoning)


def _structured_output_methods(model: object) -> tuple[str | None, ...]:
    provider = str(getattr(model, "_inquira_provider", "") or "").strip().lower()
    if provider == "ollama":
        return ("json_schema", "function_calling", "json_mode")
    return (None,)


def _is_recoverable_structured_output_error(exc: Exception) -> bool:
    message = str(exc or "").strip().lower()
    if not message:
        return False
    markers = (
        "expected value at line",
        "expecting value: line 1 column 1",
        "jsondecodeerror",
        "json error injected into sse stream",
        "outputparserexception",
        "invalid json output",
        "unsupported response_format type",
        "not support json schema",
        "structured outputs not supported",
    )
    return any(marker in message for marker in markers)


def _latest_user_text(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        msg_type = str(getattr(msg, "type", "") or "").lower()
        if msg_type in {"human", "user"}:
            return str(getattr(msg, "content", "") or "").strip()
    if messages:
        return str(getattr(messages[-1], "content", "") or "").strip()
    return ""


async def decide_route_details(messages: list[AnyMessage], configurable: dict) -> RouteDecision:
    user_text = _latest_user_text(messages)
    if _UNSAFE_RE.search(user_text):
        return RouteDecision(route="unsafe", reasoning=_fallback_reasoning("unsafe", user_text))

    runtime = load_llm_runtime_config()
    provider = normalize_llm_provider(str(configurable.get("provider") or runtime.provider))
    base_url = str(configurable.get("base_url") or runtime.base_url).strip()
    default_model = normalize_model_id(
        str(configurable.get("default_model") or runtime.default_model).strip()
    )
    lite_model = normalize_model_id(
        str(configurable.get("lite_model") or runtime.lite_model).strip()
    )
    selected_model = normalize_model_id(str(configurable.get("model") or "").strip())
    model_name = lite_model or selected_model or default_model
    api_key = str(configurable.get("api_key") or "").strip()
    temperature = float(configurable.get("temperature") if configurable.get("temperature") is not None else 0.0)
    max_tokens = int(configurable.get("max_tokens") if configurable.get("max_tokens") is not None else 256)
    top_p = float(configurable.get("top_p") if configurable.get("top_p") is not None else 1.0)
    top_k = int(configurable.get("top_k") if configurable.get("top_k") is not None else 0)
    frequency_penalty = float(
        configurable.get("frequency_penalty") if configurable.get("frequency_penalty") is not None else 0.0
    )
    presence_penalty = float(
        configurable.get("presence_penalty") if configurable.get("presence_penalty") is not None else 0.0
    )
    if provider_requires_api_key(provider) and not api_key:
        return "analysis"

    try:
        model = create_chat_model(
            provider=provider,
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            max_tokens=max_tokens,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _ROUTER_PROMPT),
                MessagesPlaceholder("messages"),
            ]
        )
        last_exc: Exception | None = None
        decision = None
        methods = _structured_output_methods(model)
        for idx, method in enumerate(methods):
            try:
                if method is None:
                    chain = prompt | model.with_structured_output(RouteDecision)
                else:
                    try:
                        chain = prompt | model.with_structured_output(
                            RouteDecision,
                            method=method,
                            include_raw=False,
                        )
                    except TypeError:
                        chain = prompt | model.with_structured_output(RouteDecision)
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message=r"^Pydantic serializer warnings:",
                        category=UserWarning,
                    )
                    decision = await chain.ainvoke({"messages": messages})
                break
            except Exception as exc:
                last_exc = exc
                if idx >= len(methods) - 1:
                    raise
                if not _is_recoverable_structured_output_error(exc):
                    raise
        if decision is None and last_exc is not None:
            raise last_exc
        normalized = _normalize_decision(decision, user_text)
        if normalized.route in {"analysis", "general_chat", "unsafe"}:
            return normalized
    except Exception:
        pass

    analysis_hints = re.compile(
        r"\b(chart|plot|graph|sql|query|average|sum|count|group by|dataset|table|column)\b",
        re.IGNORECASE,
    )
    fallback_route = "analysis" if analysis_hints.search(user_text) else "general_chat"
    return RouteDecision(route=fallback_route, reasoning=_fallback_reasoning(fallback_route, user_text))


async def decide_route(messages: list[AnyMessage], configurable: dict) -> str:
    return (await decide_route_details(messages, configurable)).route
