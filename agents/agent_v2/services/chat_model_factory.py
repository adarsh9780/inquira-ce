"""Factory for provider-specific LangChain chat model clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


@dataclass(frozen=True)
class ChatModelSettings:
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float
    top_p: float | None
    top_k: int | None
    frequency_penalty: float | None
    presence_penalty: float | None
    max_tokens: int | None
    max_retries: int
    timeout: float


Builder = Callable[[ChatModelSettings], BaseChatModel]


def _with_optional(kwargs: dict[str, Any], **values: Any) -> dict[str, Any]:
    for key, value in values.items():
        if value is not None:
            kwargs[key] = value
    return kwargs


def _positive_int(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    return int(value)


def _normalize_ollama_base_url(base_url: str) -> str:
    value = str(base_url or "").strip().rstrip("/") or "http://localhost:11434"
    lowered = value.lower()
    suffixes = ("/api", "/v1")
    for suffix in suffixes:
        if lowered.endswith(suffix):
            return value[: -len(suffix)].rstrip("/") or "http://localhost:11434"
    return value


def _build_openai_client(settings: ChatModelSettings) -> BaseChatModel:
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "temperature": settings.temperature,
        "max_retries": settings.max_retries,
        "timeout": settings.timeout,
    }
    _with_optional(
        kwargs,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        frequency_penalty=settings.frequency_penalty,
        presence_penalty=settings.presence_penalty,
    )
    return ChatOpenAI(**kwargs)


def _build_openrouter_client(settings: ChatModelSettings) -> BaseChatModel:
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "api_key": settings.api_key,
        "base_url": settings.base_url,
        "temperature": settings.temperature,
        "max_retries": settings.max_retries,
        "timeout": settings.timeout,
    }
    _with_optional(
        kwargs,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        top_k=_positive_int(settings.top_k),
    )
    return ChatOpenAI(**kwargs)


def _build_openai_provider_client(settings: ChatModelSettings) -> BaseChatModel:
    return _build_openai_client(settings)


def _build_ollama_client(settings: ChatModelSettings) -> BaseChatModel:
    try:
        from langchain_ollama import ChatOllama
    except ImportError as exc:  # pragma: no cover - depends on install state
        raise ValueError(
            "Provider 'ollama' requires langchain-ollama to be installed."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": settings.model,
        "base_url": _normalize_ollama_base_url(settings.base_url),
        "temperature": settings.temperature,
        "num_predict": settings.max_tokens,
        "top_p": settings.top_p,
        "top_k": _positive_int(settings.top_k),
    }
    return ChatOllama(**_with_optional({}, **kwargs))


def _build_anthropic_client(settings: ChatModelSettings) -> BaseChatModel:
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:  # pragma: no cover - depends on optional install state
        raise ValueError(
            "Provider 'anthropic' requires langchain-anthropic to be installed."
        ) from exc

    kwargs: dict[str, Any] = {
        "model": settings.model,
        "api_key": settings.api_key,
        "temperature": settings.temperature,
        "max_retries": settings.max_retries,
        "timeout": settings.timeout,
    }
    _with_optional(
        kwargs,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        top_k=_positive_int(settings.top_k),
    )
    return ChatAnthropic(**kwargs)


_PROVIDER_BUILDERS: dict[str, Builder] = {
    "openrouter": _build_openrouter_client,
    "openai": _build_openai_provider_client,
    "ollama": _build_ollama_client,
    "anthropic": _build_anthropic_client,
}


def create_chat_model(
    *,
    provider: str,
    model: str,
    api_key: str = "",
    base_url: str = "",
    temperature: float = 0,
    top_p: float | None = None,
    top_k: int | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
    max_tokens: int | None = None,
    max_retries: int = 0,
    timeout: float = 60.0,
) -> BaseChatModel:
    provider_name = str(provider or "").strip().lower()
    builder = _PROVIDER_BUILDERS.get(provider_name)
    if builder is None:
        supported = ", ".join(sorted(_PROVIDER_BUILDERS))
        raise ValueError(f"Unsupported LLM provider '{provider}'. Supported providers: {supported}.")
    settings = ChatModelSettings(
        provider=provider_name,
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        max_tokens=max_tokens,
        max_retries=max_retries,
        timeout=timeout,
    )
    model_instance = builder(settings)
    setattr(model_instance, "_inquira_provider", provider_name)
    return model_instance
