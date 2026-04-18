import types
import sys

import pytest

from app.services.chat_model_factory import create_chat_model


def test_factory_openrouter(monkeypatch):
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.services.chat_model_factory.ChatOpenAI", FakeChatOpenAI)
    create_chat_model(
        provider="openrouter",
        model="google/gemini-2.5-flash",
        api_key="k1",
        base_url="https://openrouter.ai/api/v1",
        max_tokens=512,
    )

    assert captured["model"] == "google/gemini-2.5-flash"
    assert captured["api_key"] == "k1"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["max_tokens"] == 512


def test_factory_openai(monkeypatch):
    captured = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("app.services.chat_model_factory.ChatOpenAI", FakeChatOpenAI)
    create_chat_model(
        provider="openai",
        model="gpt-4o-mini",
        api_key="k2",
        base_url="https://api.openai.com/v1",
    )

    assert captured["model"] == "gpt-4o-mini"
    assert captured["api_key"] == "k2"
    assert captured["base_url"] == "https://api.openai.com/v1"


def test_factory_ollama(monkeypatch):
    captured = {}

    class FakeChatOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = types.SimpleNamespace(ChatOllama=FakeChatOllama)
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake_module)
    create_chat_model(
        provider="ollama",
        model="llama3.2",
        api_key="",
        base_url="http://localhost:11434/v1",
        max_tokens=256,
        top_k=20,
    )

    assert captured["model"] == "llama3.2"
    assert captured["base_url"] == "http://localhost:11434"
    assert captured["num_predict"] == 256
    assert captured["top_k"] == 20


def test_factory_anthropic(monkeypatch):
    captured = {}

    class FakeChatAnthropic:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = types.SimpleNamespace(ChatAnthropic=FakeChatAnthropic)
    monkeypatch.setitem(sys.modules, "langchain_anthropic", fake_module)
    create_chat_model(
        provider="anthropic",
        model="claude-3-5-sonnet-latest",
        api_key="k3",
        max_tokens=128,
    )

    assert captured["model"] == "claude-3-5-sonnet-latest"
    assert captured["api_key"] == "k3"
    assert captured["max_tokens"] == 128


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_chat_model(provider="mystery", model="m")
