from __future__ import annotations

import sys
import types

import pytest

from agent_v2.services.chat_model_factory import create_chat_model


def test_factory_openrouter_uses_openrouter_parameter_subset(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("agent_v2.services.chat_model_factory.ChatOpenAI", FakeChatOpenAI)
    create_chat_model(
        provider="openrouter",
        model="google/gemini-2.5-flash",
        api_key="k1",
        base_url="https://openrouter.ai/api/v1",
        max_tokens=512,
        top_p=0.9,
        top_k=40,
        frequency_penalty=0.4,
        presence_penalty=0.2,
    )

    assert captured["max_tokens"] == 512
    assert captured["top_p"] == 0.9
    assert captured["top_k"] == 40
    assert "frequency_penalty" not in captured
    assert "presence_penalty" not in captured


def test_factory_openai_does_not_send_top_k(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("agent_v2.services.chat_model_factory.ChatOpenAI", FakeChatOpenAI)
    create_chat_model(
        provider="openai",
        model="gpt-4o-mini",
        api_key="k2",
        base_url="https://api.openai.com/v1",
        top_k=40,
        frequency_penalty=0.4,
        presence_penalty=0.2,
    )

    assert "top_k" not in captured
    assert captured["frequency_penalty"] == 0.4
    assert captured["presence_penalty"] == 0.2


def test_factory_ollama_uses_native_langchain_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = types.SimpleNamespace(ChatOllama=FakeChatOllama)
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)

    create_chat_model(
        provider="ollama",
        model="minimax-m2.7:cloud",
        api_key="ignored",
        base_url="http://localhost:11434/api",
        max_tokens=512,
        top_p=0.8,
        top_k=40,
    )

    assert captured["model"] == "minimax-m2.7:cloud"
    assert captured["base_url"] == "http://localhost:11434"
    assert captured["num_predict"] == 512
    assert captured["top_p"] == 0.8
    assert captured["top_k"] == 40
    assert "api_key" not in captured


def test_factory_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_chat_model(provider="mystery", model="m")
