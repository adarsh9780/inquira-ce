from types import SimpleNamespace

import pytest

from app.v1.services.chat_service import ChatService


class _TrackingSession:
    def __init__(self) -> None:
        self.commits = 0
        self._in_transaction = True

    def in_transaction(self) -> bool:
        return self._in_transaction

    async def commit(self) -> None:
        self.commits += 1
        self._in_transaction = False


def _llm_preferences() -> dict[str, object]:
    return {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "requires_api_key": False,
        "selected_lite_model": "openai/gpt-4.1-mini",
        "selected_main_model": "google/gemini-2.5-flash",
        "selected_coding_model": "google/gemini-2.5-flash",
        "temperature": 0.0,
        "max_tokens": 2048,
        "top_p": 1.0,
        "top_k": 0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "allow_llm_data_samples": False,
    }


@pytest.mark.asyncio
async def test_stream_chat_releases_db_transaction_before_agent_stream(monkeypatch):
    session = _TrackingSession()

    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="Conversation"), "conv-1", {}, "", "/tmp/ws.db")

    async def _fake_resolve_llm_preferences(_session, _user_id):
        return _llm_preferences()

    async def _fake_persist_turn(**_kwargs):
        return "turn-1"

    async def _fake_health(_self):
        assert session.commits == 1
        assert session.in_transaction() is False
        return {"status": "ok", "api_major": 1}

    async def _fake_stream(_self, _payload):
        assert session.commits == 1
        assert session.in_transaction() is False
        yield {
            "event": "values",
            "data": {
                "run_id": "run-1",
                "metadata": {"is_safe": True, "is_relevant": True},
                "final_code": "",
                "final_explanation": "done",
                "messages": [],
            },
        }

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_resolve_llm_preferences", staticmethod(_fake_resolve_llm_preferences))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", _fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.stream", _fake_stream)

    events = [
        event
        async for event in ChatService.analyze_and_stream_turns(
            session=session,
            langgraph_manager=None,
            user=SimpleNamespace(id="user-1", username="alice"),
            workspace_id="ws-1",
            conversation_id="conv-1",
            question="hello",
            current_code="",
            model="google/gemini-2.5-flash",
            context=None,
        )
    ]

    assert session.commits == 1
    assert events[-1]["event"] == "final"


@pytest.mark.asyncio
async def test_non_stream_chat_releases_db_transaction_before_agent_run(monkeypatch):
    session = _TrackingSession()

    async def _fake_preflight(**_kwargs):
        return (SimpleNamespace(title="Conversation"), "conv-2", {}, "", "/tmp/ws.db")

    async def _fake_resolve_llm_preferences(_session, _user_id):
        return _llm_preferences()

    async def _fake_persist_turn(**_kwargs):
        return "turn-2"

    async def _fake_health(_self):
        assert session.commits == 1
        assert session.in_transaction() is False
        return {"status": "ok", "api_major": 1}

    async def _fake_run(_self, _payload):
        assert session.commits == 1
        assert session.in_transaction() is False
        return {
            "route": "analysis",
            "metadata": {"is_safe": True, "is_relevant": True},
            "final_code": "",
            "final_explanation": "done",
            "messages": [],
        }

    monkeypatch.setattr(ChatService, "_preflight_check", staticmethod(_fake_preflight))
    monkeypatch.setattr(ChatService, "_resolve_llm_preferences", staticmethod(_fake_resolve_llm_preferences))
    monkeypatch.setattr(ChatService, "_persist_turn", staticmethod(_fake_persist_turn))
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.assert_health", _fake_health)
    monkeypatch.setattr("app.v1.services.chat_service.AgentClient.run", _fake_run)

    payload, conversation_id, turn_id = await ChatService.analyze_and_persist_turn(
        session=session,
        langgraph_manager=None,
        user=SimpleNamespace(id="user-2", username="bob"),
        workspace_id="ws-1",
        conversation_id="conv-2",
        question="hello",
        current_code="",
        model="google/gemini-2.5-flash",
        context=None,
    )

    assert session.commits == 1
    assert conversation_id == "conv-2"
    assert turn_id == "turn-2"
    assert payload["result_explanation"] == "done"
