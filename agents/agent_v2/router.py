"""Routing logic for agent v2."""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Literal

from langchain_core.messages import AnyMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel

from .services.chat_model_factory import create_chat_model
from .services.llm_runtime_config import load_llm_runtime_config, normalize_model_id
from .services.llm_provider_catalog import normalize_llm_provider, provider_requires_api_key

_ROUTER_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "router_system.yaml"
).read_text(encoding="utf-8")

_UNSAFE_RE = re.compile(
    r"\b(rm\s+-rf|drop\s+table|truncate\s+table|delete\s+from|exfiltrate|steal|bypass)\b",
    re.IGNORECASE,
)


class RouteDecision(BaseModel):
    route: Literal["analysis", "general_chat", "unsafe"]


def _latest_user_text(messages: list[AnyMessage]) -> str:
    for msg in reversed(messages):
        msg_type = str(getattr(msg, "type", "") or "").lower()
        if msg_type in {"human", "user"}:
            return str(getattr(msg, "content", "") or "").strip()
    if messages:
        return str(getattr(messages[-1], "content", "") or "").strip()
    return ""


async def decide_route(messages: list[AnyMessage], configurable: dict) -> str:
    user_text = _latest_user_text(messages)
    if _UNSAFE_RE.search(user_text):
        return "unsafe"

    runtime = load_llm_runtime_config()
    provider = normalize_llm_provider(str(configurable.get("provider") or runtime.provider))
    base_url = str(configurable.get("base_url") or runtime.base_url).strip()
    default_model = normalize_model_id(
        str(configurable.get("default_model") or runtime.default_model).strip()
    )
    lite_model = normalize_model_id(
        str(configurable.get("lite_model") or runtime.lite_model).strip()
    )
    if provider == "ollama":
        analysis_hints = re.compile(
            r"\b(chart|plot|graph|sql|query|average|sum|count|group by|dataset|table|column)\b",
            re.IGNORECASE,
        )
        return "analysis" if analysis_hints.search(user_text) else "general_chat"

    selected_model = normalize_model_id(str(configurable.get("model") or "").strip())
    model_name = lite_model or selected_model or default_model
    api_key = str(configurable.get("api_key") or "").strip()
    if provider_requires_api_key(provider) and not api_key:
        return "analysis"

    try:
        model = create_chat_model(
            provider=provider,
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=256,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _ROUTER_PROMPT),
                MessagesPlaceholder("messages"),
            ]
        )
        chain = prompt | model.with_structured_output(RouteDecision)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"^Pydantic serializer warnings:",
                category=UserWarning,
            )
            decision = await chain.ainvoke({"messages": messages})
        route = str(getattr(decision, "route", "")).strip().lower()
        if route in {"analysis", "general_chat", "unsafe"}:
            return route
    except Exception:
        pass

    analysis_hints = re.compile(
        r"\b(chart|plot|graph|sql|query|average|sum|count|group by|dataset|table|column)\b",
        re.IGNORECASE,
    )
    return "analysis" if analysis_hints.search(user_text) else "general_chat"
