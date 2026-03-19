"""Factory for provider-specific LangChain chat model clients."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


def _build_openai_client(
    *,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int | None,
    max_retries: int,
    timeout: float,
) -> BaseChatModel:
    kwargs: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": temperature,
        "max_retries": max_retries,
        "timeout": timeout,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatOpenAI(**kwargs)


def create_chat_model(
    *,
    provider: str,
    model: str,
    api_key: str = "",
    base_url: str = "",
    temperature: float = 0,
    max_tokens: int | None = None,
    max_retries: int = 0,
    timeout: float = 60.0,
) -> BaseChatModel:
    provider_name = str(provider or "").strip().lower()

    if provider_name in {"openrouter", "openai"}:
        return _build_openai_client(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            timeout=timeout,
        )

    if provider_name == "ollama":
        return _build_openai_client(
            model=model,
            api_key=api_key or "ollama",
            base_url=base_url or "http://localhost:11434/v1",
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            timeout=timeout,
        )

    if provider_name == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:  # pragma: no cover - depends on optional install state
            raise ValueError(
                "Provider 'anthropic' requires langchain-anthropic to be installed."
            ) from exc

        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "temperature": temperature,
            "max_retries": max_retries,
            "timeout": timeout,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        return ChatAnthropic(**kwargs)

    raise ValueError(
        f"Unsupported LLM provider '{provider}'. Supported providers: openrouter, openai, ollama, anthropic."
    )
