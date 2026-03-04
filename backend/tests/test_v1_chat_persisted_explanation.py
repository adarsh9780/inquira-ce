from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


class _FakeGraph:
    def __init__(self, result):
        self._result = result

    async def ainvoke(self, _input_state, config=None):  # noqa: ARG002
        return dict(self._result)


class _FakeLanggraphManager:
    def __init__(self, result):
        self._result = result

    async def get_graph(self, _workspace_id, _memory_path):
        return _FakeGraph(self._result)


def _build_execution_result() -> dict:
    return {
        "success": True,
        "stdout": "",
        "stderr": "",
        "error": None,
        "artifacts": [{"artifact_id": "a-1", "kind": "scalar"}],
    }


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_uses_final_explanation_for_assistant_text(monkeypatch):
    captured = {}

    async def fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-1", {}, "table_1", "/tmp/ws.duckdb")

    async def fake_persist_turn(*, response_payload, **_kwargs):
        captured["assistant_text"] = response_payload["explanation"]
        return "turn-1"

    async def fake_execute(**_kwargs):
        return _build_execution_result(), 0, 10.0, "print('hello')"

    async def fake_finalize(**_kwargs):
        return None

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(fake_persist_turn))
    monkeypatch.setattr(ChatService, "_execute_generated_code_with_retries", staticmethod(fake_execute))
    monkeypatch.setattr(ChatService, "_finalize_kernel_run", staticmethod(fake_finalize))

    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "print('hello')",
        "final_explanation": "This code prints a greeting and verifies runtime execution.",
        "plan": "Fallback plan explanation",
        "messages": [],
    }

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=_FakeLanggraphManager(result),
        user=SimpleNamespace(id="user-1", username="alice"),
        workspace_id="ws-1",
        conversation_id=None,
        question="Print hello",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
        api_key="test-api-key",
    )

    assert conversation_id == "conv-1"
    assert turn_id == "turn-1"
    assert payload["explanation"] == "This code prints a greeting and verifies runtime execution."
    assert captured["assistant_text"] == "This code prints a greeting and verifies runtime execution."


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_falls_back_to_plan_when_final_explanation_missing(monkeypatch):
    captured = {}

    async def fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-2", {}, "table_1", "/tmp/ws.duckdb")

    async def fake_persist_turn(*, response_payload, **_kwargs):
        captured["assistant_text"] = response_payload["explanation"]
        return "turn-2"

    async def fake_execute(**_kwargs):
        return _build_execution_result(), 0, 8.0, "print('fallback')"

    async def fake_finalize(**_kwargs):
        return None

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(fake_persist_turn))
    monkeypatch.setattr(ChatService, "_execute_generated_code_with_retries", staticmethod(fake_execute))
    monkeypatch.setattr(ChatService, "_finalize_kernel_run", staticmethod(fake_finalize))

    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "print('fallback')",
        "final_explanation": "",
        "plan": "Fallback explanation from plan node.",
        "messages": [],
    }

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=_FakeLanggraphManager(result),
        user=SimpleNamespace(id="user-1", username="alice"),
        workspace_id="ws-1",
        conversation_id=None,
        question="Run fallback",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
        api_key="test-api-key",
    )

    assert conversation_id == "conv-2"
    assert turn_id == "turn-2"
    assert payload["explanation"] == "Fallback explanation from plan node."
    assert captured["assistant_text"] == "Fallback explanation from plan node."
