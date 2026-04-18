from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from agent_v2.nodes import _get_model, analysis_assess_context_node
from agent_v2.router import decide_route


def _runtime_stub() -> SimpleNamespace:
    return SimpleNamespace(
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="default-model",
        lite_model="lite-model",
        schema_max_tokens=2048,
        code_generation_max_tokens=4096,
    )


def test_get_model_prefers_lite_model_for_lite_tasks(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("agent_v2.nodes.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.nodes.provider_requires_api_key", lambda _provider: False)

    def fake_create_chat_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("agent_v2.nodes.create_chat_model", fake_create_chat_model)

    _get_model(
        {
            "configurable": {
                "provider": "openrouter",
                "base_url": "https://openrouter.ai/api/v1",
                "model": "selected-main-model",
                "lite_model": "preferred-lite-model",
                "default_model": "fallback-default-model",
            }
        },
        lite=True,
    )

    assert captured.get("model") == "preferred-lite-model"


def test_get_model_uses_coding_model_then_selected_for_non_lite_tasks(monkeypatch) -> None:
    monkeypatch.setattr("agent_v2.nodes.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.nodes.provider_requires_api_key", lambda _provider: False)

    captured_models: list[str] = []

    def fake_create_chat_model(**kwargs):
        captured_models.append(str(kwargs.get("model") or ""))
        return object()

    monkeypatch.setattr("agent_v2.nodes.create_chat_model", fake_create_chat_model)

    _get_model(
        {
            "configurable": {
                "model": "selected-main-model",
                "coding_model": "preferred-coding-model",
                "default_model": "fallback-default-model",
            }
        },
        lite=False,
    )
    _get_model(
        {
            "configurable": {
                "model": "selected-main-model",
                "coding_model": "",
                "default_model": "fallback-default-model",
            }
        },
        lite=False,
    )

    assert captured_models == ["preferred-coding-model", "selected-main-model"]


def test_get_model_uses_schema_token_budget_for_lite_path(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("agent_v2.nodes.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.nodes.provider_requires_api_key", lambda _provider: False)

    def fake_create_chat_model(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("agent_v2.nodes.create_chat_model", fake_create_chat_model)

    _get_model(
        {
            "configurable": {
                "provider": "openrouter",
                "model": "selected-main-model",
                "lite_model": "preferred-lite-model",
                "default_model": "fallback-default-model",
            }
        },
        lite=True,
    )

    assert int(captured.get("max_tokens") or 0) == 2048


@pytest.mark.asyncio
async def test_analysis_assess_context_uses_non_lite_model_path(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakePrompt:
        def __or__(self, other):
            return other

    class _FakeModel:
        def with_structured_output(self, _schema):
            return object()

    def fake_get_model(_config, *, lite):
        captured["lite"] = lite
        return _FakeModel()

    async def fake_ainvoke(_chain, _payload):
        return {"enough_context": True, "missing_context": [], "tool_plan": []}

    monkeypatch.setattr("agent_v2.nodes._get_model", fake_get_model)
    monkeypatch.setattr("agent_v2.nodes.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())
    monkeypatch.setattr("agent_v2.nodes._ainvoke_structured_chain", fake_ainvoke)

    result = await analysis_assess_context_node(
        {
            "analysis_context": {
                "messages": [HumanMessage(content="show top performers")],
                "user_text": "show top performers",
                "schema_summary": "orders(id, revenue)",
                "table_names": ["orders"],
            },
            "known_columns": [],
        },
        {"configurable": {}},
    )

    assert captured.get("lite") is False
    assert result.get("context_sufficiency", {}).get("enough_context") is True


@pytest.mark.asyncio
async def test_router_prefers_lite_model_for_route_decision(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakePrompt:
        def __or__(self, other):
            return other

    class _FakeModel:
        def with_structured_output(self, _schema):
            return self

        async def ainvoke(self, _payload):
            return SimpleNamespace(route="analysis")

    monkeypatch.setattr("agent_v2.router.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.router.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())

    def fake_create_chat_model(**kwargs):
        captured.update(kwargs)
        return _FakeModel()

    monkeypatch.setattr("agent_v2.router.create_chat_model", fake_create_chat_model)

    route = await decide_route(
        [HumanMessage(content="can you help me plan this?")],
        {
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": "test-key",
            "model": "selected-main-model",
            "lite_model": "preferred-lite-model",
            "default_model": "fallback-default-model",
        },
    )

    assert route == "analysis"
    assert captured.get("model") == "preferred-lite-model"


@pytest.mark.asyncio
async def test_router_uses_model_for_ollama_route_decision(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakePrompt:
        def __or__(self, other):
            return other

    class _FakeModel:
        def with_structured_output(self, _schema):
            return self

        async def ainvoke(self, _payload):
            return SimpleNamespace(route="general_chat")

    monkeypatch.setattr("agent_v2.router.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.router.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())

    def fake_create_chat_model(**kwargs):
        captured.update(kwargs)
        return _FakeModel()

    monkeypatch.setattr("agent_v2.router.create_chat_model", fake_create_chat_model)

    route = await decide_route(
        [HumanMessage(content="hello")],
        {
            "provider": "ollama",
            "base_url": "http://localhost:11434/v1",
            "model": "minimax-m2.7:cloud",
            "lite_model": "minimax-m2.7:cloud",
            "default_model": "llama3.2",
        },
    )

    assert route == "general_chat"
    assert captured.get("provider") == "ollama"
    assert captured.get("model") == "minimax-m2.7:cloud"


@pytest.mark.asyncio
async def test_router_falls_back_structured_output_method_for_ollama(monkeypatch) -> None:
    class _FakePrompt:
        def __or__(self, other):
            return other

    class _FakeChain:
        def __init__(self, method: str):
            self.method = method

        async def ainvoke(self, _payload):
            if self.method == "json_schema":
                raise ValueError("JSONDecodeError: Expecting value: line 1 column 1 (char 0)")
            return SimpleNamespace(route="general_chat")

    class _FakeModel:
        _inquira_provider = "ollama"

        def __init__(self):
            self.methods: list[str] = []

        def with_structured_output(self, _schema, *, method=None, include_raw=False):
            _ = include_raw
            selected_method = str(method or "")
            self.methods.append(selected_method)
            return _FakeChain(selected_method)

    fake_model = _FakeModel()

    monkeypatch.setattr("agent_v2.router.load_llm_runtime_config", _runtime_stub)
    monkeypatch.setattr("agent_v2.router.ChatPromptTemplate.from_messages", lambda *_args, **_kwargs: _FakePrompt())
    monkeypatch.setattr("agent_v2.router.create_chat_model", lambda **_kwargs: fake_model)

    route = await decide_route(
        [HumanMessage(content="hello")],
        {
            "provider": "ollama",
            "base_url": "http://localhost:11434/v1",
            "model": "minimax-m2.7:cloud",
            "lite_model": "minimax-m2.7:cloud",
            "default_model": "llama3.2",
        },
    )

    assert route == "general_chat"
    assert fake_model.methods[:2] == ["json_schema", "function_calling"]
