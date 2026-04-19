from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


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
    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self, payload
        return dict(result)

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=None,
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
    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self, payload
        return dict(result)

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=None,
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


@pytest.mark.asyncio
async def test_analyze_and_persist_turn_does_not_execute_stale_current_code(monkeypatch):
    captured = {}

    async def fake_preflight(**_kwargs):
        return (SimpleNamespace(title="New Conversation"), "conv-3", {}, "table_1", "/tmp/ws.duckdb")

    async def fake_persist_turn(*, response_payload, **_kwargs):
        captured["assistant_text"] = response_payload["explanation"]
        captured["metadata"] = dict(response_payload.get("metadata") or {})
        return "turn-3"

    async def fail_execute(**_kwargs):
        raise AssertionError("runtime execution should not run for stale current_code-only payloads")

    async def fail_finalize(**_kwargs):
        raise AssertionError("kernel finalize should not run for stale current_code-only payloads")

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(fake_preflight))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(fake_persist_turn))
    monkeypatch.setattr(ChatService, "_execute_generated_code_with_retries", staticmethod(fail_execute))
    monkeypatch.setattr(ChatService, "_finalize_kernel_run", staticmethod(fail_finalize))

    result = {
        "metadata": {"is_safe": True, "is_relevant": True},
        "current_code": "print('stale')",
        "final_explanation": "I could not complete this analysis.",
        "messages": [],
    }

    async def fake_health(self):
        _ = self
        return {"status": "ok", "api_major": 1}

    async def fake_run(self, payload):
        _ = self, payload
        return dict(result)

    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", fake_run)

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=object(),
        langgraph_manager=None,
        user=SimpleNamespace(id="user-1", username="alice"),
        workspace_id="ws-1",
        conversation_id=None,
        question="Run stale code?",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
        api_key="test-api-key",
    )

    assert conversation_id == "conv-3"
    assert turn_id == "turn-3"
    assert payload["explanation"] == "I could not complete this analysis."
    assert captured["assistant_text"] == "I could not complete this analysis."
    assert captured["metadata"].get("result_explanation") == "I could not complete this analysis."
