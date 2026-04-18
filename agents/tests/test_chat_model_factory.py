from __future__ import annotations

import sys
import types

import pytest

from agent_v2.services.chat_model_factory import create_chat_model


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
